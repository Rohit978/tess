import os
import json
import logging
from .logger import setup_logger
from .config import Config

logger = setup_logger("SkillManager")

class SkillManager:
    """
    Manages user-taught skills (macros).
    Skills are stored as JSON plans in `data/skills/{user_id}/`.
    """
    def __init__(self, user_id="default"):
        self.user_id = str(user_id)
        self.skills_dir = os.path.join("data", "skills", self.user_id)
        os.makedirs(self.skills_dir, exist_ok=True)
        self.skills_cache = {}
        self._load_skills()

    def _load_skills(self):
        """Loads all skills into memory for quick lookup."""
        try:
            for filename in os.listdir(self.skills_dir):
                if filename.endswith(".json"):
                    skill_name = filename[:-5] # remove .json
                    filepath = os.path.join(self.skills_dir, filename)
                    with open(filepath, 'r', encoding='utf-8') as f:
                        self.skills_cache[skill_name] = json.load(f)
            logger.info(f"Loaded {len(self.skills_cache)} skills for user {self.user_id}")
        except Exception as e:
            logger.error(f"Failed to load skills: {e}")

    def learn_skill(self, name, goal, planner):
        """
        Creates a plan for the goal and saves it as a skill.
        Returns the generated plan.
        """
        logger.info(f"Learning new skill: '{name}' for goal: '{goal}'")
        
        # 1. Generate Plan
        plan = planner.create_plan(goal)
        if not plan:
            return None
            
        # 2. Save Skill
        skill_data = {
            "name": name,
            "goal": goal,
            "plan": plan,
            "created_at": str(os.path.getctime(self.skills_dir) if os.path.exists(self.skills_dir) else 0) # Fallback timestamp
        }
        
        # Normalize name for filename
        safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '_', '-')).strip()
        filepath = os.path.join(self.skills_dir, f"{safe_name}.json")
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(skill_data, f, indent=2)
            
            # Update cache
            self.skills_cache[safe_name] = skill_data
            return plan
        except Exception as e:
            logger.error(f"Failed to save skill '{name}': {e}")
            return None

    def get_skill(self, name):
        """Exact or fuzzy match for a skill."""
        # Direct match
        if name in self.skills_cache:
            return self.skills_cache[name]
            
        # Case-insensitive match
        for key, skill in self.skills_cache.items():
            if key.lower() == name.lower():
                return skill
                
        return None

    def list_skills(self):
        """Returns a list of all available skill names."""
        return list(self.skills_cache.keys())

    def delete_skill(self, name):
        """Deletes a skill."""
        if name in self.skills_cache:
            safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '_', '-')).strip()
            filepath = os.path.join(self.skills_dir, f"{safe_name}.json")
            if os.path.exists(filepath):
                os.remove(filepath)
            del self.skills_cache[name]
            return True
        return False
