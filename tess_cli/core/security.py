from .logger import setup_logger
import re

logger = setup_logger("SecurityEngine")

class SecurityEngine:
    """
    The Guardian: Validates actions before execution.
    Prevents accidental system destruction or unauthorized access.
    """
    def __init__(self, level="MEDIUM"):
        self.level = level.upper() # HIGH, MEDIUM, LOW
        
        # Dangerous Commands Blacklist (Regex)
        self.dangerous_patterns = [
            r"rm\s+-rf",           # Unix destroy
            r"del\s+/s",           # Windows destroy recursive
            r"format\s+[c-z]:",    # Format drive
            r"rd\s+/s",            # Remove directory recursive
            r"net\s+user",         # Network user manipulation
            r"shutdown",           # Shutdown command
            r"taskkill",           # Task killing (unless specific)
            r"reg\s+delete",       # Registry deletion
        ]
        
        # Sensitive Paths Blacklist
        self.sensitive_paths = [
            r"C:\\Windows",
            r"C:\\Program Files",
            r"C:\\Users\\[^\\]+\\AppData", # AppData usually hidden/system
            r"System32",
        ]

    def validate_action(self, action_dict):
        """
        Validates a TESS action.
        Returns: (is_safe: bool, reason: str)
        """
        action_type = action_dict.get("action")
        
        # 1. Execute Command Validation
        if action_type == "execute_command":
            cmd = action_dict.get("command", "").lower()
            
            # Check Dangerous Patterns
            for pattern in self.dangerous_patterns:
                if re.search(pattern, cmd):
                    return False, f"Blocked Dangerous Command Pattern: {pattern}"
            
            # Check Sensitive Paths
            for path in self.sensitive_paths:
                if path.lower() in cmd:
                    return False, f"Blocked Access to Sensitive Path: {path}"
            
            # High Security: Block significant file modifications
            if self.level == "HIGH" and any(x in cmd for x in [">", ">>", "write", "set-content"]):
                 return False, "High Security Mode blocks file writes."

        # 2. File Operation Validation
        elif action_type == "file_op":
            sub_action = action_dict.get("sub_action")
            path = action_dict.get("path", "")
            
            if sub_action in ["write", "patch", "delete"]:
                 # Check Sensitive Paths
                for sp in self.sensitive_paths:
                    if sp.lower() in path.lower():
                        return False, f"Blocked Write/Delete on Sensitive Path: {sp}"

        # 3. System Control Validation
        elif action_type == "system_control":
             # Generally safe, unless we restrict screenshots for privacy
             pass
             
        # Default: Safe
        return True, "Action Permitted"

    def set_level(self, level):
        self.level = level.upper()
        logger.info(f"Security Level set to {self.level}")
