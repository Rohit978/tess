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
        
    def read_file(self, filename, start_line=None, end_line=None):
        """Read file contents, optionally a line range (1-indexed)."""
        file_path = os.path.join(self.workspace_root, filename)
        if not os.path.exists(file_path):
            return f"Error: {filename} not found."
        
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
        except Exception as e:
            return f"Error reading file: {e}"
        
        total = len(lines)
        if start_line or end_line:
            s = max(1, start_line or 1) - 1
            e = min(total, end_line or total)
            selected = lines[s:e]
            return f"[{filename}] Lines {s+1}-{e} of {total}\n" + "".join(selected)
        
        return f"[{filename}] {total} lines\n" + "".join(lines[:300])

    def scaffold_project(self, project_type, path):
        """Create a new project structure with GSD spec files."""
        if not path:
            return "Error: Project path is required for scaffolding."
        if not project_type:
            project_type = "python"
            
        target_path = os.path.join(self.workspace_root, path)
        os.makedirs(target_path, exist_ok=True)
        
        # Initialize GSD Workspace
        from .gsd_workspace import GSDWorkspace
        gsd = GSDWorkspace(target_path)
        gsd_msg = gsd.init_workspace(project_name=os.path.basename(path))
        
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
        return f"Successfully scaffolded {project_type} project at {path}.\n{gsd_msg}"

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
        
        # Use Brain's parser to handle markdown blocks
        response = self.brain.request_completion([{"role": "system", "content": prompt}], json_mode=True)
        try:
            data = self.brain._parse_json(response)
            
            fixed_code = data.get("fixed_code") or data.get("code") or data.get("solution")
            if fixed_code:
                self.write_file(filename, fixed_code)
                return f"Applied fix to {filename}. Retesting recommended."
        except Exception as e:
            return f"Failed to parse fix: {e}"
        return "Failed to generate autonomous fix."

    def review_code(self, filename):
        """Static analysis and code review."""
        file_path = os.path.join(self.workspace_root, filename)
        if not os.path.exists(file_path):
            return f"Error: {filename} not found."

        with open(file_path, "r", encoding="utf-8") as f:
            code = f.read()

        prompt = f"""
        TESS Tech Lead: Code Review
        FILE: {filename}
        CODE:
        ```python
        {code}
        ```

        Provide a concise code review covering:
        1.  **Bugs**: Logic errors, potential crashes.
        2.  **Security**: Vulnerabilities, hardcoded secrets.
        3.  **Style**: Readability, PEP8 compliance.
        4.  **Optimization**: Performance improvements.

        Format as Markdown.
        """
        return self.brain.request_completion([{"role": "system", "content": prompt}]) or "Review failed."

    def debug_code(self, filename):
        """Auto-Run -> Analyze -> Fix Loop."""
        logger.info(f"Debugging {filename}...")
        
        # 1. Run the code
        result = self.execute(filename)
        
        # 2. Check for errors
        if "Traceback" not in result and "Error" not in result:
             return f"Code ran successfully:\n{result}"
             
        # 3. Analyze and Fix
        logger.info(f"Error detected in {filename}. Attempting fix...")
        fix_result = self.fix_code(filename, result)
        
        if "Applied fix" in fix_result:
            # 4. Retry once
            retry_res = self.execute(filename)
            if "Traceback" not in retry_res:
                return f"✅ Fixed and Verified!\nOriginal Error: {result[:100]}...\nFix: {fix_result}\nOutput: {retry_res}"
            else:
                return f"⚠️ Fix applied but error persists.\n{retry_res}"
        
        return f"❌ Could not fix error automatically.\n{result}"

    def grep_search(self, pattern, path=".", include_exts=None):
        """Fast text search across files using gitignore-aware pathspec."""
        import pathspec
        import re
        
        target_path = os.path.normpath(os.path.join(self.workspace_root, path))
        if not os.path.exists(target_path):
            return f"Error: Path {path} not found."

        # Load gitignore if exists
        spec = None
        gitignore_path = os.path.join(self.workspace_root, ".gitignore")
        if os.path.exists(gitignore_path):
            with open(gitignore_path, "r") as f:
                spec = pathspec.PathSpec.from_lines('gitwildmatch', f)

        results = []
        pattern_re = re.compile(pattern, re.IGNORECASE)

        for root, dirs, files in os.walk(target_path):
            # Filtering hidden dirs and gitignored ones
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            
            for f in files:
                rel_path = os.path.relpath(os.path.join(root, f), self.workspace_root)
                
                # Check gitignore
                if spec and spec.match_file(rel_path):
                    continue
                
                # Check extensions
                if include_exts and not any(f.endswith(ext) for ext in include_exts):
                    continue

                abs_f = os.path.join(root, f)
                try:
                    with open(abs_f, 'r', encoding='utf-8', errors='ignore') as f_obj:
                        lines = f_obj.readlines()
                        for i, line in enumerate(lines):
                            if pattern_re.search(line):
                                results.append(f"{rel_path}:{i+1}: {line.strip()}")
                except Exception:
                    continue
        
        if not results:
            return "No matches found."
        
        # Limit results for LLM context
        return "\n".join(results[:50]) + (f"\n... total {len(results)} matches" if len(results) > 50 else "")

    def get_file_outline(self, filename):
        """Extract structure from Python (classes/funcs) or Markdown (headers) files."""
        import ast
        
        file_path = os.path.join(self.workspace_root, filename)
        if not os.path.exists(file_path):
            return f"Error: {filename} not found."
        
        # Markdown Support
        if filename.endswith('.md'):
            try:
                outline = []
                with open(file_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.startswith("#"):
                            outline.append(line.strip())
                return "\n".join(outline) if outline else "No headers found."
            except Exception as e:
                return f"Error parsing markdown: {e}"

        # Python Support
        if not filename.endswith('.py'):
            return "Error: Outline only supported for .py and .md files."

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                node = ast.parse(f.read())
            
            outline = []
            for item in node.body:
                if isinstance(item, ast.ClassDef):
                    methods = [n.name for n in item.body if isinstance(n, ast.FunctionDef)]
                    outline.append(f"Class: {item.name} (Methods: {', '.join(methods)})")
                elif isinstance(item, ast.FunctionDef):
                    outline.append(f"Function: {item.name}")
            
            return "\n".join(outline) if outline else "No classes or functions found."
        except Exception as e:
            return f"Error parsing file: {e}"

        # Generic Text Fallback
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                head = [next(f) for _ in range(50)]
            if not head: return "Empty file."
            return "".join(head) + ("\n... (truncated)" if len(head) == 50 else "")
        except Exception as e:
            return f"Error reading file: {e}"

    def replace_block(self, filename, search_block, replace_block):
        """Surgical edit: replaces a specific block of text with whitespace normalization and atomic write."""
        import tempfile
        
        file_path = os.path.join(self.workspace_root, filename)
        if not os.path.exists(file_path):
            return f"Error: {filename} not found."

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Helper to normalize whitespace for comparison
            def normalize(text):
                return "\n".join([line.rstrip() for line in text.strip().splitlines()])

            if search_block not in content:
                # If exact match fails, try normalized match
                norm_search = normalize(search_block)
                lines = content.splitlines()
                match_found = False
                
                # Simple sliding window search on lines
                search_lines = search_block.splitlines()
                for i in range(len(lines) - len(search_lines) + 1):
                    window = "\n".join(lines[i:i+len(search_lines)])
                    if normalize(window) == norm_search:
                        # Found match! Perform replacement
                        lines[i:i+len(search_lines)] = replace_block.splitlines()
                        content = "\n".join(lines)
                        match_found = True
                        break
                
                if not match_found:
                    return f"Error: Search block not found in {filename}. Ensure the code block is unique and correctly copied."
            else:
                content = content.replace(search_block, replace_block)

            # Atomic Write using a temporary file
            fd, temp_path = tempfile.mkstemp(dir=os.path.dirname(file_path), text=True)
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Replace original file with temporary file
            os.replace(temp_path, file_path)
            
            return f"Successfully updated {filename} (Atomic Write)"
        except Exception as e:
            if 'temp_path' in locals() and os.path.exists(temp_path):
                os.remove(temp_path)
            return f"Error during replacement: {e}"

    def ls_recursive(self, path="."):
        """Tree view of the workspace."""
        import pathspec
        
        target_path = os.path.normpath(os.path.join(self.workspace_root, path))
        if not os.path.exists(target_path):
            return f"Error: Path {path} not found."

        spec = None
        gitignore_path = os.path.join(self.workspace_root, ".gitignore")
        if os.path.exists(gitignore_path):
            with open(gitignore_path, "r") as f:
                spec = pathspec.PathSpec.from_lines('gitwildmatch', f)

        tree = []
        for root, dirs, files in os.walk(target_path):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            level = root.replace(target_path, '').count(os.sep)
            indent = '  ' * level
            folder = os.path.basename(root)
            if folder:
                tree.append(f"{indent}📁 {folder}/")
            
            sub_indent = '  ' * (level + 1)
            for f in files:
                rel_path = os.path.relpath(os.path.join(root, f), self.workspace_root)
                if spec and spec.match_file(rel_path):
                    continue
                tree.append(f"{sub_indent}📄 {f}")
        
        return "\n".join(tree[:100]) # Limit output
