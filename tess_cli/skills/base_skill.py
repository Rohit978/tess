
from abc import ABC, abstractmethod

class BaseSkill(ABC):
    """
    Abstract Base Class for all TESS Skills.
    
    If you want to add a new ability to TESS, inherit from this class.
    Define which 'intents' (action types) you handle, and implement execute().
    """
    
    name: str = "base_skill"
    description: str = "Description of what this skill does."
    
    # List of action types this skill handles (e.g. ['broadcast_op', 'spotify_op'])
    intents: list[str] = [] 

    def __init__(self, brain=None, config=None):
        """
        Initialize the skill. 
        Args:
            brain: The Brain instance (for LLM access).
            config: Optional config dict.
        """
        self.brain = brain
        self.config = config or {}

    @abstractmethod
    def execute(self, action_data: dict, context: dict) -> str:
        """
        Execute the requested action.
        
        Args:
            action_data (dict): The full JSON action object from the LLM.
            context (dict): Additional runtime context (if needed).
            
        Returns:
            str: The result message to send back to the user/logs.
        """
        pass
