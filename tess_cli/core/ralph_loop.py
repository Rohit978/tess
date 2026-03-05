"""
Ralph Orchestrator
Implements the 'Ralph' autonomous coding agent loop:
Stateless LLM invocations that read external spec files (PRD, task),
execute a single coding task, test it, and commit/revert via git.
"""

import os
import subprocess
import json
from .logger import setup_logger
from .gsd_workspace import GSDWorkspace
from .terminal_ui import print_info, print_success, print_error, print_warning

logger = setup_logger("RalphLoop")

class RalphOrchestrator:
    def __init__(self, coding_engine):
        """
        Requires access to the CodingEngine for executing the actual code edits,
        tests, and reading files.
        """
        self.coding_engine = coding_engine
        
    def _git_commit(self, path, message):
        """Commit current changes to local git."""
        try:
            # Ensure git repo exists
            if not os.path.exists(os.path.join(path, ".git")):
                subprocess.run(["git", "init"], cwd=path, capture_output=True)
                
            subprocess.run(["git", "add", "."], cwd=path, capture_output=True)
            res = subprocess.run(["git", "commit", "-m", message], cwd=path, capture_output=True, text=True)
            return "nothing to commit" not in res.stdout.lower()
        except Exception as e:
            logger.error(f"Git commit failed: {e}")
            return False

    def _git_revert(self, path):
        """Revert uncommitted changes if a test failed."""
        try:
            if os.path.exists(os.path.join(path, ".git")):
                subprocess.run(["git", "reset", "--hard", "HEAD"], cwd=path, capture_output=True)
                subprocess.run(["git", "clean", "-fd"], cwd=path, capture_output=True)
        except Exception as e:
            logger.error(f"Git revert failed: {e}")

    def run_loop(self, workspace_path, max_iterations=10):
        """
        The core Ralph autonomous loop.
        """
        target_path = os.path.abspath(workspace_path)
        if not os.path.exists(target_path):
            print_error(f"Workspace {workspace_path} does not exist.")
            return

        gsd = GSDWorkspace(target_path)
        self.coding_engine.workspace_root = target_path # Point engine to target
        
        print_info(f"Starting Ralph Loop on {target_path}")
        
        for iteration in range(1, max_iterations + 1):
            print_info(f"\n--- ⚡ RALPH ITERATION {iteration}/{max_iterations} ---")
            
            # 1. State Reading (GSD specs + Git status)
            state_context = gsd.get_state()
            if not state_context:
                print_warning("No GSD specs found. Run `scaffold_project` first, or manually create prd.md.")
                break
                
            # 2. Compile the Prompt for the stateless Brain
            prompt = f"""
            You are Ralph, an autonomous software engineer.
            Your job is to read the Project State below, pick EXACTLY ONE step from the `task.md` plan that is unchecked, and write the code to solve it.
            
            PROJECT STATE:
            {state_context}
            
            OUTPUT:
            Respond STRICTLY in JSON format indicating the file you want to edit and the FULL code it should contain.
            Also include the name of the task you are completing.
            
            Format:
            {{
                "task_name": "Implement user login",
                "filename": "src/auth.py",
                "code": "def login()...",
                "completed": true
            }}
            
            If all tasks in task.md are checked off, return {{"completed": true, "task_name": "DONE"}}.
            """
            
            # 3. Stateless Call (Wipe conversation history)
            brain = self.coding_engine.brain
            # Backup history
            old_history = list(brain.history)
            
            brain.history = [{"role": "system", "content": "You are Ralph, a precise JSON-only coding agent."}]
            
            print_info("Analyzing PRD and strategizing next code edit...")
            response = brain.request_completion([{"role": "user", "content": prompt}], json_mode=True)
            
            # Restore history
            brain.history = old_history
            
            # 4. Parse execution plan
            try:
                action = brain._parse_json(response)
            except Exception as e:
                print_error(f"Ralph hallucinated non-JSON output: {e}\nAborting iteration.")
                continue
                
            task_name = action.get("task_name", "Unknown Task")
            filename = action.get("filename")
            code = action.get("code")
            
            if task_name == "DONE":
                print_success("🎉 Ralph completed all tasks in the PRD/task.md!")
                break
                
            if not filename or not code:
                 print_warning(f"Ralph returned incomplete action for: {task_name}")
                 continue
                 
            print_info(f"Writing [{filename}] to resolve: {task_name}")
            
            # 5. Execute Code Write
            write_res = self.coding_engine.write_file(filename, code)
            if "Error" in write_res:
                print_error(write_res)
                continue
                
            # 6. Test and Verify
            print_info("Running test suite...")
            # We assume a basic 'pytest' run for Python projects
            test_res = self.coding_engine.test_project()
            
            if "FAILED" in test_res or "Error" in test_res[:50]:
                print_error("Tests failed! Reverting changes (stateless retry on next loop).")
                self._git_revert(target_path)
            else:
                print_success("Tests passed! Committing work.")
                self._git_commit(target_path, f"Auto (Ralph): {task_name}")
                # Update GSD spec
                gsd.update_task_status(task_name, completed=True)
                
        print_info("Ralph Loop concluded.")
