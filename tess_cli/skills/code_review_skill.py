import os
import json
import time
from datetime import datetime
from tess_cli.skills.base_skill import BaseSkill
from tess_cli.core.terminal_ui import print_tess_action

class CodeReviewSkill(BaseSkill):
    """
    TESS Code Review Feature.
    Reviews local files, directories, or git diffs for bugs, security, performance, and style issues.
    Generates a structured Markdown report.
    """
    name = "CodeReview"
    description = "AI code reviewer for local files and git diffs."
    intents = ["review_op"]

    def execute(self, action_data: dict, context: dict) -> str:
        sub_action = action_data.get("sub_action", "diff")
        path = action_data.get("path")
        diff_content = action_data.get("content")
        
        self.output_handler = context.get("output_handler")

        code_to_review = ""
        target_name = "unknown"

        if sub_action == "file":
            if not path or not os.path.isfile(path):
                return "Error: Please provide a valid file path to review."
            try:
                with open(path, "r", encoding="utf-8") as f:
                    code_to_review = f.read()
                target_name = path
            except Exception as e:
                return f"Error reading file {path}: {e}"
                
        elif sub_action == "directory":
            if not path or not os.path.isdir(path):
                return "Error: Please provide a valid directory path to review."
            # Read all python/js/etc files
            allowed_exts = {".py", ".js", ".ts", ".html", ".css", ".go", ".rs", ".cpp", ".c", ".java"}
            snippets = []
            for root, _, files in os.walk(path):
                # Ignore common ignored dirs
                if any(x in root for x in [".git", "__pycache__", "node_modules", "venv", ".venv"]):
                    continue
                for file in files:
                    ext = os.path.splitext(file)[1].lower()
                    if ext in allowed_exts:
                        filepath = os.path.join(root, file)
                        try:
                            with open(filepath, "r", encoding="utf-8") as f:
                                snippets.append(f"--- File: {filepath} ---\n{f.read()}")
                        except:
                            pass
            code_to_review = "\n\n".join(snippets)
            target_name = f"Directory: {path}"
            if not code_to_review:
                return f"Error: No supported source code files found in {path}."

        elif sub_action == "diff":
            if diff_content:
                code_to_review = diff_content
                target_name = "Git Diff"
            else:
                # Try to get diff from executor
                exe = context.get("components", {}).get("executor")
                if not exe:
                    return "Error: Executor component not available to run git diff."
                
                # Check staged first, then unstaged
                out = exe.execute_command("git diff --cached")
                if not out.strip() or "ERROR:" in out:
                    out = exe.execute_command("git diff")
                
                if not out.strip() or "ERROR:" in out:
                    return "No uncommitted git changes found to review."
                code_to_review = out
                target_name = "Uncommitted Git Changes"
        else:
            return f"Error: Unsupported review sub_action '{sub_action}'"

        if not code_to_review.strip():
            return "Error: Target is empty. Nothing to review."

        print_tess_action(f"Deep reviewing {target_name}...")
        
        # Analyze using Brain
        report_json = self._analyze_code(code_to_review, target_name)
        if not report_json:
            return "Error: Failed to generate review from the AI model."

        # Render Markdown
        markdown_report = self._render_markdown(report_json, target_name)
        
        # Save to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"review_{timestamp}.md"
        report_path = os.path.join(os.getcwd(), report_filename)
        
        try:
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(markdown_report)
            return f"Review completed. Report saved to {report_filename}\n\nSummary: {report_json.get('summary', 'No summary provided.')}"
        except Exception as e:
            return f"Review completed but failed to save report: {e}\n\nSummary: {report_json.get('summary')}"

    def _analyze_code(self, code: str, target_name: str) -> dict:
        """Sends the code to the LLM and requests a structured JSON response."""
        # Trim if excessively huge (prevent context overflow)
        max_chars = 30000
        if len(code) > max_chars:
            code = code[:max_chars] + "\n... (truncated for length)"

        prompt = f"""
You are TESS CodeReview, an expert AI software engineer and security auditor.
Your job is to review the following code/diff and find issues.

TARGET: {target_name}

CODE:
```
{code}
```

INSTRUCTIONS:
Analyze the code for:
1. Bugs (logic errors, nil pointers, exception risks)
2. Security (injection vulnerabilities, hardcoded secrets, bad CORS, insecure defaults)
3. Performance (O(N^2) loops, memory leaks, unoptimized queries)
4. Style (readability, clean code principles, DRY)

OUTPUT STRICTLY AS JSON:
{{
    "summary": "A 2-3 sentence overall assessment of the code.",
    "bugs": [
        {{"line": "line number or range", "severity": "HIGH/MEDIUM/LOW", "issue": "description", "fix": "suggestion"}}
    ],
    "security": [
         {{"line": "line number or range", "severity": "CRITICAL/HIGH/MEDIUM", "issue": "description", "fix": "suggestion"}}
    ],
    "performance": [
         {{"line": "line number or range", "issue": "description", "fix": "suggestion"}}
    ],
    "style": [
         {{"line": "line number or range", "issue": "description"}}
    ]
}}

Ensure valid JSON syntax. Do NOT use markdown code blocks around the JSON output.
"""
        try:
            # We bypass the generic brain memory/history here and do a raw completion
            raw_response = self.brain.request_completion([{"role": "user", "content": prompt}], temperature=0.2)
            # Use Brain's robust json parser
            return self.brain._parse_json(raw_response)
        except Exception as e:
            print_tess_action(f"Analysis failed: {e}")
            return None

    def _render_markdown(self, data: dict, target_name: str) -> str:
        """Converts the structured JSON into a beautiful Markdown report."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        md = f"# 🔍 TESS Code Review — {target_name}\n"
        md += f"Generated: {timestamp}\n\n"
        
        md += "## 📊 Summary\n"
        md += f"{data.get('summary', 'No summary available.')}\n\n"
        
        # Helper to render tables
        def render_table(title, items, columns, keys):
            if not items:
                return f"## {title} (0)\nNo issues found.\n\n"
            
            section = f"## {title} ({len(items)})\n"
            section += "|" + "|".join(columns) + "|\n"
            section += "|" + "|".join(["---"] * len(columns)) + "|\n"
            
            for item in items:
                row = []
                for key in keys:
                    val = str(item.get(key, "")).replace("\n", " ").replace("|", "\\|")
                    row.append(val)
                section += "|" + "|".join(row) + "|\n"
            
            return section + "\n"

        md += render_table("🐛 Bugs", data.get("bugs", []), 
                         ["Line", "Severity", "Issue", "Suggested Fix"], 
                         ["line", "severity", "issue", "fix"])
                         
        md += render_table("🔒 Security", data.get("security", []), 
                         ["Line", "Severity", "Issue", "Suggested Fix"], 
                         ["line", "severity", "issue", "fix"])
                         
        md += render_table("⚡ Performance", data.get("performance", []), 
                         ["Line", "Issue", "Suggested Fix"], 
                         ["line", "issue", "fix"])
                         
        md += render_table("🎨 Style", data.get("style", []), 
                         ["Line", "Issue"], 
                         ["line", "issue"])
                         
        return md
