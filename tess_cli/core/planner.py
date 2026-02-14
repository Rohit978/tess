import json
import os
from .logger import setup_logger
from .config import Config

logger = setup_logger("Planner")

class Planner:
    """
    Decomposes complex goals into a sequence of atomic TESS actions.
    """
    def __init__(self, brain):
        self.brain = brain
        # self.client and self.model are no longer needed as we use brain.request_completion
        
    def create_plan(self, goal):
        """
        Returns a list of action dictionaries.
        """
        logger.info(f"Planning for goal: {goal}")
        
        desktop_path = Config.get_desktop_path()
        downloads_path = Config.get_downloads_path()
        docs_path = Config.get_documents_path()
        
        prompt = f"""
        You are the STRATEGIC PLANNER for TESS.
        GOAL: "{goal}"
        
        [CURRENT CONTEXT]
        - Desktop Path: {desktop_path}
        - Downloads Path: {downloads_path}
        - Documents Path: {docs_path}
        
        RULES:
        - If the user says "Desktop", ALWAYS use "{desktop_path}".
        - If the user says "Downloads", ALWAYS use "{downloads_path}".
        - If the user says "Documents", ALWAYS use "{docs_path}".
        
        Your job is to break this goal into a sequence of ATOMIC actions.
        Available Actions:
        1. code_op (scaffold, write, execute, test, fix, analyze, summarize)
        2. file_op (write, read, list, patch)
        3. execute_command (run commands)
        4. browser_control (open urls, new tab)
        5. knowledge_op (learn, search)
        
        Return a strict JSON object with a "plan" key containing a list of actions.
        The actions must match the TESS JSON schema exactly.
        
        EXAMPLE: "Build a python weather app"
        {{
            "plan": [
                {{ "action": "code_op", "sub_action": "scaffold", "project_type": "python", "path": "weather_app", "reason": "Creating project structure" }},
                {{ "action": "code_op", "sub_action": "write", "filename": "weather_app/src/main.py", "content": "print('Weather info')", "reason": "Writing entry point" }},
                {{ "action": "code_op", "sub_action": "test", "filename": "weather_app/src/main.py", "reason": "Testing core logic" }}
            ]
        }}

        """
        
        try:
            # Use Brain's centralized request methods
            messages = [{"role": "system", "content": prompt}]
            content = self.brain.request_completion(messages, temperature=0.2, json_mode=True)
            
            if not content:
                logger.error("Planning failed: LLM returned no content.")
                return []
                
            try:
                data = json.loads(content)
                plan = data.get("plan", [])
                logger.info(f"Generated plan with {len(plan)} steps.")
                return plan
            except json.JSONDecodeError:
                # Fallback if model wraps in code block
                if "```" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                    data = json.loads(content)
                    return data.get("plan", [])
                return []
                
        except Exception as e:
            logger.error(f"Planning failed: {e}")
            return []
