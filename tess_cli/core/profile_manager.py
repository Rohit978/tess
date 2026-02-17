from .brain import Brain
from .logger import setup_logger
from .skill_manager import SkillManager

logger = setup_logger("ProfileManager")

class ProfileManager:
    """
    Manages multiple user profiles, each with its own Brain and Memory.
    """
    def __init__(self, knowledge_db=None):
        self.knowledge_db = knowledge_db
        self.profiles = {} # {user_id: BrainInstance}

    def get_brain(self, user_id):
        """
        Retrieves the brain for a specific user. 
        Creates a new one if it doesn't exist.
        """
        uid = str(user_id)
        if uid not in self.profiles:
            logger.debug(f"Creating new profile for user: {uid}")
            brain = Brain(user_id=uid, knowledge_db=self.knowledge_db)
            
            # Initialize Skill Manager for this user
            brain.skill_manager = SkillManager(user_id=uid)
            
            self.profiles[uid] = brain
        
        return self.profiles[uid]

    def reset_profile(self, user_id):
        """
        Resets a user's session history (short-term memory).
        """
        uid = str(user_id)
        if uid in self.profiles:
            self.profiles[uid].history = []
            logger.info(f"Reset history for user: {uid}")
            return True
        return False
