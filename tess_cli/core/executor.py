import subprocess
import os

class Executor:
    """
    Executes shell commands with safety checks.
    """
    
    def __init__(self, safe_mode=True):
        self.safe_mode = safe_mode

    def execute_command(self, command):
        """
        Executes a shell command after user confirmation.
        """
        if not command:
            return "ERROR: No command to execute."
            
        print(f"\n[TESS] Proposed Command: {command}")
        
        if self.safe_mode:
            confirmation = input("Execute this command? (Y/n): ").strip().lower()
            if confirmation not in ['y', 'yes', 'ok', '']:
                return "Command execution cancelled by user."
        
        try:
            # Execute the command
            # Execute the command using PowerShell explicitly
            # Use list format to handle nested quotes correctly
            if "powershell" in command.lower() or command.lower().startswith("pwsh"):
                # User already specified powershell, run as is
                full_command = command
                shell_mode = True
            else:
                # Wrap in powershell -Command
                # Using a list avoids shell=True quoting hell for the outer command
                full_command = ["powershell", "-NoProfile", "-Command", command]
                shell_mode = False
            
            result = subprocess.run(
                full_command, 
                shell=shell_mode, 
                capture_output=True, 
                text=True, 
                cwd=os.getcwd()
            )
            
            output = result.stdout
            if result.stderr:
                output += f"\n[STDERR]: {result.stderr}"
                
            return output
            
        except Exception as e:
            return f"ERROR: Execution failed. {str(e)}"
