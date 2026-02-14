import os
import subprocess
import sys
from .logger import setup_logger

logger = setup_logger("Architect")

class Architect:
    """
    The Architect: Writes and executes Python scripts autonomously.
    Includes a sandbox mechanism to prevent accidental damage.
    """
    
    def __init__(self, workspace_dir="workspace"):
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

    def execute_and_fix(self, filename, brain, max_retries=3):
        """
        Executes the script. If it fails, asks Brain to fix it, rewrites, and retries.
        """
        for attempt in range(max_retries + 1):
            logger.info(f"Execution Attempt {attempt+1}/{max_retries+1} for {filename}")
            
            # 1. Execute
            output = self.execute_script(filename)
            
            # 2. Check for Errors in Output
            # Heuristic: If "Traceback" or "Error:" is in the output (stderr is merged in execute_script)
            if "Traceback (most recent call last)" in output or "Error:" in output:
                if attempt < max_retries:
                    logger.warning(f"Script failed. Triggering Self-Healing (Attempt {attempt+1})...")
                    
                    # 3. Read the broken code
                    try:
                        with open(os.path.join(self.scripts_dir, filename if filename.endswith(".py") else filename+".py"), 'r') as f:
                            code = f.read()
                    except:
                        code = "Could not read file."

                    # 4. Ask Brain to Fix
                    prompt = f"""
                    The Python script '{filename}' failed with the following output:
                    
                    {output}
                    
                    Here is the broken code:
                    ```python
                    {code}
                    ```
                    
                    TASK: Fix the code to resolve the error.
                    OUTPUT: ONLY the full corrected Python code. No markdown formatting if possible, or wrapped in ```python.
                    """
                    
                    json_prompt = prompt + '\\nReturn JSON: {"corrected_code": "..."}'
                    
                    response = brain.think(json_prompt)
                    
                    # Parse response
                    new_code = response
                    import json
                    try:
                        clean_res = response.replace("```json", "").replace("```", "").strip()
                        data = json.loads(clean_res)
                        if "corrected_code" in data:
                            new_code = data["corrected_code"]
                    except:
                        # Fallback: Extract between ```python and ```
                        if "```python" in response:
                            new_code = response.split("```python")[1].split("```")[0].strip()
                        elif "```" in response:
                            new_code = response.split("```")[1].split("```")[0].strip()
                            
                    # 5. Overwrite file
                    self.write_script(filename, new_code)
                    logger.info("Applied fix. Retrying...")
                    continue
                else:
                    return f"Execution failed after {max_retries} retries.\\nLast Output:\\n{output}"
            else:
                # Success (or no obvious error)
                return output
                
        return output
