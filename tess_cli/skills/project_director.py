import os
import time
import subprocess
import json
from ..core.terminal_ui import print_info, print_success, print_warning, print_error, print_thinking

class ProjectDirector:
    """
    Micro-manager for spec-driven development (Spec -> Plan -> Execute).
    """
    def __init__(self, brain):
        self.brain = brain
        self.root = os.getcwd()
        self.files = {
            "project": os.path.join(self.root, "PROJECT.md"),
            "roadmap": os.path.join(self.root, "ROADMAP.md"),
            "plan": os.path.join(self.root, "CURRENT_PLAN.md"),
            "state": os.path.join(self.root, "STATE.md")
        }

    def init_project(self):
        """Scaffolds the GSD files."""
        if not os.path.exists(self.files["project"]):
            with open(self.files["project"], "w", encoding="utf-8") as f:
                f.write("# Specs\n\n## Tech Stack\n- Python 3.10+\n")
            print_success("Created PROJECT.md")
        
        if not os.path.exists(self.files["roadmap"]):
            with open(self.files["roadmap"], "w", encoding="utf-8") as f:
                f.write("# Roadmap\n\n- [ ] Phase 1: MVP\n")
            print_success("Created ROADMAP.md")
        
        return "Project initialized."

    def create_plan(self, goal):
        """Drafts a micro-task plan."""
        print_thinking("Planning...")
        
        ctx = ""
        if os.path.exists(self.files["project"]):
            with open(self.files["project"], "r") as f: ctx = f.read()
            
        prompt = f"CONTEXT:\n{ctx}\nGOAL: {goal}\n\nCreate a step-by-step unnested Markdown checklist. Atomic steps only."
        plan = self.brain.think(prompt)
        
        with open(self.files["plan"], "w", encoding="utf-8") as f:
            f.write(f"# Plan: {goal}\n\n{plan}")
            
        print_success(f"Plan saved to CURRENT_PLAN.md")
        return plan

    def execute_next_step(self):
        """Pops the next task and executes it."""
        if not os.path.exists(self.files["plan"]): return "No plan."
            
        lines = []
        with open(self.files["plan"], "r") as f: lines = f.readlines()
        
        # Find next task
        target, idx = None, -1
        for i, line in enumerate(lines):
            if "- [ ]" in line:
                target = line.replace("- [ ]", "").strip()
                idx = i
                break
                
        if not target: return "Plan complete."
            
        print_info(f"👉 Step: {target}")
        print_thinking("Coding...")
        
        prompt = f"Task: {target}\nReturn JSON: {{filename, content, commit_msg}}"
        
        try:
            resp = self.brain.request_completion([{"role": "user", "content": prompt}], json_mode=True)
            action = json.loads(resp)
            
            # Write key file
            fname = action.get("filename")
            if fname and action.get("content"):
                with open(fname, "w", encoding="utf-8") as f:
                    f.write(action.get("content"))
                print_success(f"Wrote {fname}")
                
                # Auto-commit
                msg = action.get("commit_msg", f"feat: {target}")
                subprocess.run(["git", "add", "."], check=True)
                subprocess.run(["git", "commit", "-m", msg], check=True)
                print_success("Committed.")
                
                # Tick off task
                lines[idx] = lines[idx].replace("- [ ]", "- [x]")
                with open(self.files["plan"], "w") as f: f.writelines(lines)
                
                return f"Done: {target}"
            return "Gen failed."
                
        except Exception as e:
            return f"Error: {e}"

    def loop(self, goal):
        """Main loop."""
        print_info(f"🎬 Director: {goal}")
        self.init_project()
        self.create_plan(goal)
        
        while True:
            res = self.execute_next_step()
            print_info(res)
            if "Plan complete" in res: break
            time.sleep(1)
