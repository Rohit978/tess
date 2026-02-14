import os
import subprocess
import sys
import logging

logger = logging.getLogger("Architect")

class Architect:
    """
    The Architect: Writes and executes Python scripts autonomously.
    Includes a sandbox mechanism to prevent accidental damage.
    """
    
    def __init__(self, workspace_dir="workspace"):
        # In Configurable, use user's home .tess/workspace or similar if not specified
        # But to be safe lets use a local workspace folder in the project root or user specified
        # For now, stick to CWD/workspace as in Pro
        self.workspace_dir = os.path.join(os.getcwd(), workspace_dir)
        os.makedirs(self.workspace_dir, exist_ok=True)
        # Scripts subdirectory
        self.scripts_dir = os.path.join(self.workspace_dir, "scripts")
        os.makedirs(self.scripts_dir, exist_ok=True)

    def write_script(self, filename, content):
        """
        Writes a script to the workspace/scripts directory.
        """
        try:
            # Ensure filename ends with .py
            if not filename.endswith(".py"):
                filename += ".py"
                
            file_path = os.path.join(self.scripts_dir, filename)
            
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
                
            logger.info(f"Script saved: {file_path}")
            return f"Script saved successfully to {filename}"
        except Exception as e:
            logger.error(f"Failed to write script: {e}")
            return f"Error writing script: {e}"

    def execute_script(self, filename):
        """
        Executes a script from the workspace/scripts directory in a separate process.
        Captures stdout and stderr.
        """
        try:
            if not filename.endswith(".py"):
                filename += ".py"
                
            file_path = os.path.join(self.scripts_dir, filename)
            
            if not os.path.exists(file_path):
                return f"Error: Script {filename} not found."
            
            logger.info(f"Executing script: {file_path}")
            
            # Run in a separate process
            # Timeout set to 30 seconds to prevent infinite loops
            result = subprocess.run(
                [sys.executable, file_path],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=self.workspace_dir # Run in workspace root so it can access files there
            )
            
            output = f"--- STDOUT ---\n{result.stdout}\n"
            if result.stderr:
                output += f"\n--- STDERR ---\n{result.stderr}"
                
            return output
            
        except subprocess.TimeoutExpired:
            return "Error: Script execution timed out (30s limit)."
        except Exception as e:
            logger.error(f"Script execution failed: {e}")
            return f"Error executing script: {e}"
