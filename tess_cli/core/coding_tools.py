"""
TESS Coding Tools — Stateless tool functions for the Coding Agent.
Each tool takes explicit arguments and returns a string result.
Operates on absolute paths (not locked to a workspace root).
"""

import os
import re
import ast
import subprocess
import sys
import tempfile
from .logger import setup_logger

logger = setup_logger("CodingTools")

# ─── Constants ────────────────────────────────────────────────────────────────
MAX_READ_LINES = 500
MAX_SEARCH_RESULTS = 50
MAX_LS_ENTRIES = 100
COMMAND_TIMEOUT = 30

# Directories to always skip
SKIP_DIRS = {'.git', '__pycache__', 'node_modules', '.venv', 'venv', '.tox', 
             '.mypy_cache', '.pytest_cache', 'dist', 'build', '.eggs', '.egg-info'}


class CodingTools:
    """
    Stateless coding tools for the TESS Coding Agent.
    All paths are resolved relative to the workspace root.
    """

    def __init__(self, workspace_root):
        self.workspace_root = os.path.abspath(workspace_root)

    def _resolve(self, path):
        """Resolve a path relative to workspace root, or use absolute."""
        if os.path.isabs(path):
            return os.path.normpath(path)
        return os.path.normpath(os.path.join(self.workspace_root, path))

    # ─── read_file ────────────────────────────────────────────────────────
    def read_file(self, path, start_line=None, end_line=None):
        """Read file contents, optionally a line range (1-indexed, inclusive)."""
        abs_path = self._resolve(path)
        if not os.path.isfile(abs_path):
            return f"Error: File not found: {path}"

        try:
            with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
        except Exception as e:
            return f"Error reading file: {e}"

        total = len(lines)

        if start_line is not None or end_line is not None:
            s = max(1, start_line or 1) - 1  # Convert to 0-indexed
            e = min(total, end_line or total)
            selected = lines[s:e]
            header = f"[{os.path.basename(abs_path)}] Lines {s+1}-{e} of {total}\n"
            numbered = [f"{s+1+i:4d} | {line}" for i, line in enumerate(selected)]
            return header + "".join(numbered)

        # Full file — truncate if too long
        if total > MAX_READ_LINES:
            numbered = [f"{i+1:4d} | {line}" for i, line in enumerate(lines[:MAX_READ_LINES])]
            return (f"[{os.path.basename(abs_path)}] Showing 1-{MAX_READ_LINES} of {total} lines\n"
                    + "".join(numbered)
                    + f"\n... ({total - MAX_READ_LINES} more lines truncated)")

        numbered = [f"{i+1:4d} | {line}" for i, line in enumerate(lines)]
        return f"[{os.path.basename(abs_path)}] {total} lines\n" + "".join(numbered)

    # ─── write_file ───────────────────────────────────────────────────────
    def write_file(self, path, content):
        """Create or overwrite a file with the given content."""
        abs_path = self._resolve(path)
        
        # Enforce workspace boundary
        try:
            if os.path.commonpath([self.workspace_root, abs_path]) != self.workspace_root:
                return f"Error: Cannot write outside of workspace root ({self.workspace_root})"
        except ValueError:
            return "Error: Path validation failed (different drives?)."
            
        try:
            os.makedirs(os.path.dirname(abs_path), exist_ok=True)
            with open(abs_path, "w", encoding="utf-8") as f:
                f.write(content)
            line_count = content.count('\n') + (1 if content and not content.endswith('\n') else 0)
            return f"✅ Wrote {line_count} lines to {path}"
        except Exception as e:
            return f"Error writing file: {e}"

    # ─── edit_file ────────────────────────────────────────────────────────
    def edit_file(self, path, search, replace):
        """
        Surgical find-and-replace edit with whitespace-normalized fallback.
        Uses atomic write to prevent corruption.
        """
        abs_path = self._resolve(path)
        if not os.path.isfile(abs_path):
            return f"Error: File not found: {path}"

        try:
            with open(abs_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            return f"Error reading file: {e}"

        # Attempt exact match first
        if search in content:
            new_content = content.replace(search, replace, 1)
        else:
            # Normalized whitespace matching
            def normalize(text):
                return "\n".join(line.rstrip() for line in text.strip().splitlines())

            norm_search = normalize(search)
            lines = content.splitlines()
            search_lines = search.splitlines()
            match_found = False

            for i in range(len(lines) - len(search_lines) + 1):
                window = "\n".join(lines[i:i + len(search_lines)])
                if normalize(window) == norm_search:
                    lines[i:i + len(search_lines)] = replace.splitlines()
                    new_content = "\n".join(lines)
                    if content.endswith("\n"):
                        new_content += "\n"
                    match_found = True
                    break

            if not match_found:
                return f"Error: Search block not found in {path}. Ensure the text matches exactly."

        # Atomic write
        try:
            fd, temp_path = tempfile.mkstemp(dir=os.path.dirname(abs_path), text=True)
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                f.write(new_content)
            os.replace(temp_path, abs_path)
            return f"✅ Applied edit to {path}"
        except Exception as e:
            if 'temp_path' in locals() and os.path.exists(temp_path):
                os.remove(temp_path)
            return f"Error during edit: {e}"

    # ─── list_dir ─────────────────────────────────────────────────────────
    def list_dir(self, path="."):
        """List directory contents as a tree view, gitignore-aware."""
        abs_path = self._resolve(path)
        if not os.path.isdir(abs_path):
            return f"Error: Directory not found: {path}"

        # Try load gitignore
        spec = None
        try:
            import pathspec
            gitignore = os.path.join(self.workspace_root, ".gitignore")
            if os.path.isfile(gitignore):
                with open(gitignore, "r") as f:
                    spec = pathspec.PathSpec.from_lines('gitwildmatch', f)
        except ImportError:
            pass  # pathspec not installed, skip gitignore filtering

        tree = []
        count = 0

        for root, dirs, files in os.walk(abs_path):
            # Skip hidden and common junk directories
            dirs[:] = sorted([d for d in dirs if d not in SKIP_DIRS and not d.startswith('.')])

            level = root.replace(abs_path, '').count(os.sep)
            indent = '  ' * level
            folder = os.path.basename(root)
            if folder:
                tree.append(f"{indent}📁 {folder}/")

            sub_indent = '  ' * (level + 1)
            for fname in sorted(files):
                if fname.startswith('.'):
                    continue
                rel = os.path.relpath(os.path.join(root, fname), self.workspace_root)
                if spec and spec.match_file(rel):
                    continue
                tree.append(f"{sub_indent}📄 {fname}")
                count += 1
                if count >= MAX_LS_ENTRIES:
                    tree.append(f"\n... (truncated at {MAX_LS_ENTRIES} files)")
                    return "\n".join(tree)

        return "\n".join(tree) if tree else "Empty directory."

    # ─── grep_search ──────────────────────────────────────────────────────
    def grep_search(self, pattern, path=".", extensions=None):
        """Regex search across files. Returns matching lines with file:line context."""
        abs_path = self._resolve(path)
        if not os.path.exists(abs_path):
            return f"Error: Path not found: {path}"

        # Try load gitignore
        spec = None
        try:
            import pathspec
            gitignore = os.path.join(self.workspace_root, ".gitignore")
            if os.path.isfile(gitignore):
                with open(gitignore, "r") as f:
                    spec = pathspec.PathSpec.from_lines('gitwildmatch', f)
        except ImportError:
            pass

        try:
            pattern_re = re.compile(pattern, re.IGNORECASE)
        except re.error as e:
            return f"Error: Invalid regex pattern: {e}"

        results = []
        ext_list = extensions if extensions else None

        for root, dirs, files in os.walk(abs_path):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith('.')]

            for fname in files:
                if fname.startswith('.'):
                    continue
                if ext_list and not any(fname.endswith(ext) for ext in ext_list):
                    continue

                abs_f = os.path.join(root, fname)
                rel = os.path.relpath(abs_f, self.workspace_root)

                if spec and spec.match_file(rel):
                    continue

                try:
                    with open(abs_f, 'r', encoding='utf-8', errors='ignore') as f:
                        for i, line in enumerate(f, 1):
                            if pattern_re.search(line):
                                results.append(f"{rel}:{i}: {line.rstrip()}")
                                if len(results) >= MAX_SEARCH_RESULTS:
                                    break
                except Exception:
                    continue

                if len(results) >= MAX_SEARCH_RESULTS:
                    break
            if len(results) >= MAX_SEARCH_RESULTS:
                break

        if not results:
            return "No matches found."

        output = "\n".join(results)
        if len(results) >= MAX_SEARCH_RESULTS:
            output += f"\n... (capped at {MAX_SEARCH_RESULTS} results)"
        return output

    # ─── file_outline ─────────────────────────────────────────────────────
    def file_outline(self, path):
        """Extract structural outline from Python or Markdown files."""
        abs_path = self._resolve(path)
        if not os.path.isfile(abs_path):
            return f"Error: File not found: {path}"

        # Markdown
        if path.endswith('.md'):
            try:
                outline = []
                with open(abs_path, "r", encoding="utf-8") as f:
                    for i, line in enumerate(f, 1):
                        if line.startswith("#"):
                            outline.append(f"  L{i}: {line.strip()}")
                return "\n".join(outline) if outline else "No headers found."
            except Exception as e:
                return f"Error: {e}"

        # Python
        if path.endswith('.py'):
            try:
                with open(abs_path, "r", encoding="utf-8") as f:
                    source = f.read()
                node = ast.parse(source)
                outline = []
                for item in node.body:
                    if isinstance(item, ast.ClassDef):
                        methods = [n.name for n in item.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
                        outline.append(f"  L{item.lineno}: class {item.name}  [{', '.join(methods)}]")
                    elif isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        outline.append(f"  L{item.lineno}: def {item.name}()")
                    elif isinstance(item, (ast.Import, ast.ImportFrom)):
                        pass  # Skip imports in outline
                return "\n".join(outline) if outline else "No classes or functions found."
            except SyntaxError as e:
                return f"Syntax error in file: {e}"
            except Exception as e:
                return f"Error: {e}"

        # Generic: show first 30 lines
        try:
            with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
                head = [next(f, None) for _ in range(30)]
            head = [h for h in head if h is not None]
            if not head:
                return "Empty file."
            return "".join(head) + ("\n... (truncated)" if len(head) == 30 else "")
        except Exception as e:
            return f"Error: {e}"

    # ─── run_command ──────────────────────────────────────────────────────
    def run_command(self, command, cwd=None):
        """Execute a shell command via PowerShell. Returns stdout + stderr."""
        work_dir = cwd or self.workspace_root

        if not command or not command.strip():
            return "Error: Empty command."

        try:
            is_ps = "powershell" in command.lower() or command.lower().startswith("pwsh")
            full_cmd = command if is_ps else ["powershell", "-NoProfile", "-NonInteractive", "-Command", command]

            result = subprocess.run(
                full_cmd,
                shell=is_ps,
                capture_output=True,
                text=True,
                cwd=work_dir,
                timeout=COMMAND_TIMEOUT
            )

            output = result.stdout
            if result.stderr:
                output += f"\n[STDERR]: {result.stderr}"
            if result.returncode != 0:
                output += f"\n[Exit Code: {result.returncode}]"

            return output.strip() if output.strip() else "(No output)"

        except subprocess.TimeoutExpired:
            return f"Error: Command timed out after {COMMAND_TIMEOUT}s."
        except Exception as e:
            return f"Error executing command: {e}"

    # ─── git_status ───────────────────────────────────────────────────────
    def git_status(self, path="."):
        """Return git status of the workspace."""
        abs_path = self._resolve(path)
        try:
            result = subprocess.run(
                ["git", "status", "--short"],
                capture_output=True, text=True, cwd=abs_path, timeout=10
            )
            output = result.stdout.strip()
            return output if output else "Working tree clean."
        except Exception as e:
            return f"Error: {e}"

    # ─── git_diff ─────────────────────────────────────────────────────────
    def git_diff(self, path="."):
        """Return uncommitted diff."""
        abs_path = self._resolve(path)
        try:
            result = subprocess.run(
                ["git", "diff"],
                capture_output=True, text=True, cwd=abs_path, timeout=10
            )
            staged = subprocess.run(
                ["git", "diff", "--cached"],
                capture_output=True, text=True, cwd=abs_path, timeout=10
            )
            output = ""
            if result.stdout.strip():
                output += "=== Unstaged Changes ===\n" + result.stdout.strip()
            if staged.stdout.strip():
                output += "\n=== Staged Changes ===\n" + staged.stdout.strip()
            return output if output else "No uncommitted changes."
        except Exception as e:
            return f"Error: {e}"

    # ─── git_commit ───────────────────────────────────────────────────────
    def git_commit(self, message, path="."):
        """Stage all and commit with the given message."""
        abs_path = self._resolve(path)
        try:
            subprocess.run(["git", "add", "."], cwd=abs_path, capture_output=True, timeout=10)
            result = subprocess.run(
                ["git", "commit", "-m", message],
                capture_output=True, text=True, cwd=abs_path, timeout=10
            )
            output = result.stdout.strip()
            if result.returncode != 0:
                output += f"\n{result.stderr.strip()}"
            return output if output else "Nothing to commit."
        except Exception as e:
            return f"Error: {e}"
