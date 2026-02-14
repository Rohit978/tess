"""
Planner module - Decomposes goals into actionable steps.
"""

import json
from typing import List, Dict, Any


class Planner:
    """
    Goal decomposition planner.
    Breaks down complex tasks into step-by-step actions.
    """
    
    def __init__(self, brain=None):
        self.brain = brain
    
    def create_plan(self, goal: str) -> List[Dict[str, Any]]:
        """
        Create a plan to achieve a goal.
        
        Args:
            goal: The goal to achieve
            
        Returns:
            List of action dictionaries
        """
        if not self.brain:
            # Fallback: return simple execute command
            return [{"action": "execute_command", "command": goal, "reason": "Direct execution"}]
        
        # Use LLM to create plan
        prompt = f"""Break down this goal into 3-5 specific, actionable steps.
Each step should be a single action.

Goal: {goal}

Available actions: launch_app, execute_command, file_op, web_search_op, browser_control

Return ONLY a JSON list of steps like:
[
  {{"action": "action_name", "param": "value", "reason": "why"}},
  ...
]
"""
        
        try:
            response = self.brain.think(prompt)
            
            # Extract JSON
            import re
            match = re.search(r'\[.*\]', response, re.DOTALL)
            if match:
                plan = json.loads(match.group(0))
                return plan if isinstance(plan, list) else []
            
            return []
        except Exception as e:
            print(f"Planning error: {e}")
            return []
    
    def execute_plan(self, plan: List[Dict[str, Any]], orchestrator, output_callback=None):
        """
        Execute a plan step by step.
        
        Args:
            plan: List of action dictionaries
            orchestrator: Orchestrator instance
            output_callback: Optional output callback
        """
        results = []
        
        for i, step in enumerate(plan, 1):
            if output_callback:
                output_callback(f"\n[Step {i}/{len(plan)}] {step.get('reason', 'Executing...')}")
            
            result = orchestrator.process_action(step, output_callback)
            results.append(result)
        
        return results
