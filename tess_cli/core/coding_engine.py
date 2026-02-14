"""
TESS Coding Engine - Autonomous Software Development
Handles scaffolding, analysis, building, testing, and fixing codebases.
"""

import os
import subprocess
import sys
import json
from .logger import setup_logger
from .config import Config

logger = setup_logger("CodingEngine")

class CodingEngine:
    """
    Advanced coding module capable of multi-file project management.
    """
    
    def __init__(self, brain, workspace_dir="workspace"):
        self.brain = brain
        self.workspace_root = os.path.join(os.getcwd(), workspace_dir)
        os.makedirs(self.workspace_root, exist_ok=True)
        
    def scaffold_project(self, project_type, path):
        """Create a new project structure."""
        if not path:
            return "Error: Project path is required for scaffolding."
        if not project_type:
            project_type = "python"
            
        target_path = os.path.join(self.workspace_root, path)
        os.makedirs(target_path, exist_ok=True)
        
        if project_type == "python":
            # Python Project Scaffold
            dirs = ["src", "tests"]
            for d in dirs: os.makedirs(os.path.join(target_path, d), exist_ok=True)
            
            with open(os.path.join(target_path, "requirements.txt"), "w") as f: f.write("# Dependencies\n")
            with open(os.path.join(target_path, "README.md"), "w") as f: f.write(f"# {os.path.basename(path)}\n")
            with open(os.path.join(target_path, "src", "main.py"), "w") as f: 
                f.write("def main():\n    print('Hello TESS!')\n\nif __name__ == '__main__':\n    main()\n")
        
        elif project_type == "web":
            # Basic Web Scaffold
            with open(os.path.join(target_path, "index.html"), "w") as f:
                f.write("<!DOCTYPE html>\n<html>\n<head><title>TESS Web App</title></head>\n<body><h1>Hello TESS!</h1></body>\n</html>")
            with open(os.path.join(target_path, "style.css"), "w") as f: f.write("body { font-family: sans-serif; }")
            with open(os.path.join(target_path, "script.js"), "w") as f: f.write("console.log('TESS Web App Loaded');")
            
        logger.info(f"Scaffolded {project_type} project at {target_path}")
        return f"Successfully scaffolded {project_type} project at {path}"

    def write_file(self, filename, content):
        """Write code to a file."""
        if not filename:
            return "Error: Filename is required for writing code."
            
        file_path = os.path.join(self.workspace_root, filename)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return f"Successfully wrote to {filename}"
        except Exception as e:
            return f"Error writing file: {e}"

    def execute(self, filename):
        """Execute a Python file and return output."""
        file_path = os.path.join(self.workspace_root, filename)
        if not os.path.exists(file_path):
            return f"Error: {filename} not found."
            
        try:
            result = subprocess.run(
                [sys.executable, file_path],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=self.workspace_root
            )
            output = result.stdout
            if result.stderr:
                output += "\n--- ERRORS ---\n" + result.stderr
            return output
        except subprocess.TimeoutExpired:
            return "Error: Execution timed out."
        except Exception as e:
            return f"Error executing: {e}"

    def test_project(self, filename=None, custom_command=None):
        """Run tests and return results."""
        cmd = custom_command or (f"pytest {filename}" if filename else "pytest")
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                cwd=self.workspace_root
            )
            return result.stdout + "\n" + result.stderr
        except Exception as e:
            return f"Testing failed: {e}"

    def fix_code(self, filename, error_log):
        """Autonomous fix loop: takes error and code, asks Brain for fix."""
        file_path = os.path.join(self.workspace_root, filename)
        if not os.path.exists(file_path):
            return f"Error: {filename} not found to fix."
            
        with open(file_path, "r", encoding="utf-8") as f:
            broken_code = f.read()
            
        prompt = f"""
        TESS Co-Pilot: Bug Resolution
        FILE: {filename}
        ERROR: {error_log}
        CODE:
        ```python
        {broken_code}
        ```
        
        Analyze the error and the code. Provide the FULL corrected code.
        JSON format: {{"fixed_code": "..."}}
        """
        
        response = self.brain.request_completion([{"role": "system", "content": prompt}], json_mode=True)
        try:
            data = json.loads(response)
            fixed_code = data.get("fixed_code")
            if fixed_code:
                self.write_file(filename, fixed_code)
                return f"Applied fix to {filename}. Retesting recommended."
        except:
            pass
        return "Failed to generate autonomous fix."

    def analyze_workspace(self, path="."):
        """Deep code analysis and summarization."""
        target_path = os.path.join(self.workspace_root, path)
        files = []
        for root, _, fs in os.walk(target_path):
            for f in fs:
                if f.endswith(('.py', '.js', '.html', '.css', '.md')):
                    files.append(os.path.relpath(os.path.join(root, f), self.workspace_root))
        
        summary_prompt = f"""
        Summarize this project workspace.
        FILES: {', '.join(files[:20])}
        Structure and Purpose?
        """
        
        response = self.brain.request_completion([{"role": "system", "content": summary_prompt}])
        return response
