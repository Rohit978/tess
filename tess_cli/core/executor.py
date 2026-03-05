import subprocess
import os

class Executor:
    """Shell command execution with safety rails."""
    def __init__(self, safe_mode=True):
        self.safe_mode = safe_mode

    def execute_command(self, command):
        if not command: return "ERROR: Empty command."
            
        print(f"\n[TESS] > {command}")
        
        if self.safe_mode:
            if input("Run? (Y/n): ").strip().lower() not in ['y', 'yes', 'ok', '']:
                return "Cancelled."
        
        try:
            # force powershell for consistency
            # To prevent hangs (like Start-Process asking for input), force -NonInteractive
            is_ps = "powershell" in command.lower() or command.lower().startswith("pwsh")
            full_cmd = command if is_ps else ["powershell", "-NoProfile", "-NonInteractive", "-Command", command]
            
            res = subprocess.run(
                full_cmd, 
                shell=is_ps, 
                capture_output=True, 
                text=True, 
                cwd=os.getcwd(),
                timeout=60
            )
            
            return res.stdout + (f"\n[STDERR]: {res.stderr}" if res.stderr else "")
            
        except subprocess.TimeoutExpired:
            return "Exec Failed: Command timed out after 60 seconds."
        except Exception as e:
            return f"Exec Failed: {e}"
