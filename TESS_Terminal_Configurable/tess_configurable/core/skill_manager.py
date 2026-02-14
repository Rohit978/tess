"""
Skill Manager - Learn and reuse task patterns.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional


class SkillManager:
    """
    Manages user-taught skills (macros).
    Skills are stored as JSON plans.
    """
    
    def __init__(self, user_id: str = "default", skills_dir: Optional[str] = None):
        self.user_id = user_id
        
        if skills_dir is None:
            from ..config_manager import get_config_manager
            config = get_config_manager()
            skills_dir = config.config.paths.skills_dir
        
        self.skills_dir = Path(skills_dir)
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        
        self.skills: Dict[str, Dict] = {}
        self._load_skills()
    
    def _load_skills(self):
        """Load all skills from disk."""
        try:
            for file in self.skills_dir.glob("*.json"):
                skill_name = file.stem
                with open(file, 'r', encoding='utf-8') as f:
                    self.skills[skill_name] = json.load(f)
        except Exception as e:
            print(f"Error loading skills: {e}")
    
    def learn_skill(self, name: str, goal: str, planner) -> Optional[List[Dict]]:
        """
        Learn a new skill from a goal.
        
        Args:
            name: Skill name
            goal: What the skill should do
            planner: Planner instance to generate steps
            
        Returns:
            The generated plan if successful
        """
        print(f"Learning skill: {name}")
        
        # Generate plan
        plan = planner.create_plan(goal)
        if not plan:
            return None
        
        # Save skill
        skill_data = {
            "name": name,
            "goal": goal,
            "plan": plan,
            "created_at": str(os.path.getctime(self.skills_dir)) if os.path.exists(self.skills_dir) else ""
        }
        
        # Safe filename
        safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '_', '-')).strip().replace(' ', '_')
        filepath = self.skills_dir / f"{safe_name}.json"
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(skill_data, f, indent=2)
            
            self.skills[safe_name] = skill_data
            return plan
        except Exception as e:
            print(f"Error saving skill: {e}")
            return None
    
    def get_skill(self, name: str) -> Optional[Dict]:
        """Get a skill by name (fuzzy match)."""
        # Exact match
        if name in self.skills:
            return self.skills[name]
        
        # Case insensitive
        name_lower = name.lower().replace(' ', '_')
        for key, skill in self.skills.items():
            if key.lower() == name_lower:
                return skill
        
        return None
    
    def list_skills(self) -> List[str]:
        """List all skill names."""
        return list(self.skills.keys())
    
    def delete_skill(self, name: str) -> bool:
        """Delete a skill."""
        skill = self.get_skill(name)
        if not skill:
            return False
        
        safe_name = "".join(c for c in skill['name'] if c.isalnum() or c in (' ', '_', '-')).strip().replace(' ', '_')
        filepath = self.skills_dir / f"{safe_name}.json"
        
        try:
            if filepath.exists():
                filepath.unlink()
            del self.skills[safe_name]
            return True
        except Exception as e:
            print(f"Error deleting skill: {e}")
            return False
    
    def run_skill(self, name: str, orchestrator, output_callback=None):
        """
        Execute a skill.
        
        Args:
            name: Skill name
            orchestrator: Orchestrator instance
            output_callback: Optional output callback
        """
        skill = self.get_skill(name)
        if not skill:
            return f"Skill '{name}' not found"
        
        plan = skill.get("plan", [])
        if output_callback:
            output_callback(f"Running skill: {skill['name']}")
        
        from .planner import Planner
        planner = Planner()
        return planner.execute_plan(plan, orchestrator, output_callback)
