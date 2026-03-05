
import os
import sys
import importlib
import inspect
import logging
from ..skills.base_skill import BaseSkill

logger = logging.getLogger("SkillLoader")

class SkillLoader:
    """
    Dynamically loads skills from the 'skills' directory.
    No more hardcoding imports in cli.py! 
    """

    def __init__(self, brain):
        self.brain = brain
        self.registry = {}  # Map: intent -> skill_instance
        self.skills = {}    # Map: skill_name -> skill_instance
        
        # Internal Skills
        self.internal_skills_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "skills")
        
        # User Plugin Directory (~/.tess/plugins)
        self.user_plugins_dir = os.path.join(os.path.expanduser("~"), ".tess", "plugins")
        if not os.path.exists(self.user_plugins_dir):
            os.makedirs(self.user_plugins_dir)

    def load_skills(self):
        """Scans the skills folder and loads all valid plugins."""
        count = 0
        
        # 1. Load Internal Skills
        count += self._load_from_directory(self.internal_skills_dir, is_internal=True)
        
        # 2. Load User Plugins (Overrides internal if conflict)
        count += self._load_from_directory(self.user_plugins_dir, is_internal=False)

        logger.info(f"🎉 Total skills loaded: {count}")
        return self.registry

    def _load_from_directory(self, directory, is_internal=True):
        """Helper to scan a directory for skill plugins."""
        if not os.path.exists(directory): return 0
        
        logger.info(f"🔎 Scanning for skills in: {directory}")
        loaded_count = 0
        
        # Add to sys.path if user directory so imports work
        if not is_internal and directory not in sys.path:
            sys.path.append(directory)

        for filename in os.listdir(directory):
            if filename.endswith(".py") and not filename.startswith("__"):
                module_name = filename[:-3]
                try:
                    if is_internal:
                        # Internal Import (tess_cli.skills.xyz)
                        module_path = f"tess_cli.skills.{module_name}"
                        module = importlib.import_module(module_path)
                    else:
                        # User Import (direct file import or module from sys.path)
                        # Since we added directory to sys.path, we can just import module_name
                        module = importlib.import_module(module_name)
                    
                    # Inspect for BaseSkill subclasses
                    for name, obj in inspect.getmembers(module):
                        if (inspect.isclass(obj) and 
                            issubclass(obj, BaseSkill) and 
                            obj is not BaseSkill):
                            
                            try:
                                skill_instance = obj(brain=self.brain)
                                self._register_skill(skill_instance)
                                loaded_count += 1
                                logger.info(f"✅ Loaded Skill: {skill_instance.name} ({'Internal' if is_internal else 'User'})")
                            except Exception as e:
                                logger.error(f"Failed to instantiate {name}: {e}")

                except Exception as e:
                    logger.warning(f"⚠️ Could not load module {module_name}: {e}")
                    
        return loaded_count

    def _register_skill(self, skill: BaseSkill):
        """Maps intents to the skill instance."""
        self.skills[skill.name] = skill
        
        for intent in skill.intents:
            if intent in self.registry:
                logger.warning(f"⚠️ Conflict! Intent '{intent}' already handled by another skill. Overwriting with {skill.name}.")
            
            self.registry[intent] = skill
