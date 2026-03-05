"""
TESS Coding Agent .
An interactive REPL where TESS autonomously plans and executes multi-step
coding tasks using tools, with a permission model for dangerous operations.
"""

import os
import json
import time
from .coding_tools import CodingTools
from .coding_ui import (
    console, print_code_banner, get_code_prompt, print_thinking, clear_thinking,
    print_thought, print_tool_call, print_tool_result, ask_permission,
    print_agent_message, print_error, print_success, print_info,
    print_tess_md_loaded, print_step_count
)
from .tess_md import read_tess_md, find_tess_md
from .logger import setup_logger

logger = setup_logger("CodingAgent")

# Tools that are safe to auto-execute (no side effects)
SAFE_TOOLS = {"read_file", "list_dir", "grep_search", "file_outline", "git_status", "git_diff", "write_analysis"}

# Tools that require user permission (write/execute side effects)
DANGEROUS_TOOLS = {"write_file", "edit_file", "run_command", "git_commit"}

MAX_AGENT_STEPS = 25

# ─── Tool Schema (injected into the system prompt) ───────────────────────────
TOOL_SCHEMA_DOC = """
AVAILABLE TOOLS (respond with exactly one tool call per message):

1. read_file(path, start_line?, end_line?)
   Read a file's contents. Supports optional line range (1-indexed).

2. write_file(path, content)
   Create or overwrite a file. REQUIRES PERMISSION.

3. edit_file(path, search, replace)
   Surgical find-and-replace. The 'search' text must match exactly.
   Only replaces the FIRST occurrence. REQUIRES PERMISSION.

4. list_dir(path?)
   List directory contents as a tree. Defaults to workspace root.

5. grep_search(pattern, path?, extensions?)
   Regex search across files. 'extensions' is a list like [".py", ".js"].

6. file_outline(path)
   Get structural outline (classes/functions for .py, headers for .md).

7. run_command(command, cwd?)
   Execute a shell command (PowerShell on Windows). REQUIRES PERMISSION.

8. git_status(path?)
   Show git status of the workspace.

9. git_diff(path?)
   Show uncommitted changes.

10. git_commit(message, path?)
    Stage all and commit. REQUIRES PERMISSION.

11. write_analysis(filename, content)
    Create a structured Markdown analysis/report file in the workspace.
    Use this for analyse/review/audit/summarize tasks. Safe — no permission needed.

12. done(message)
    Finish the task and show your final response to the user.

RESPONSE FORMAT (strict JSON, no markdown wrapping):
{
    "thought": "Brief reasoning about what to do next",
    "tool": "tool_name",
    "args": { "arg1": "value1", "arg2": "value2" }
}

RULES:
- Call exactly ONE tool per response.
- Always start by understanding the codebase (read files, list dirs, search) before making changes.
- For edits, read the file first to get the exact text to search for.
- The 'done' tool is how you deliver your final answer. Its 'message' supports Markdown.
- Keep thoughts brief (1 sentence).
- If a tool returns an error, adapt your approach.
"""


class CodingAgent:
    """
    Interactive coding agent with an agentic tool loop.
    Launched via 'tess code' or by entering coding mode from the main loop.
    """

    def __init__(self, brain, workspace_path=None):
        self.brain = brain
        self.workspace_path = os.path.abspath(workspace_path or os.getcwd())
        self.tools = CodingTools(self.workspace_path)
        self.session_history = []

    def start(self, workspace_path=None):
        """Enter the interactive coding REPL."""
        if workspace_path:
            self.workspace_path = os.path.abspath(workspace_path)
            self.tools = CodingTools(self.workspace_path)

        print_code_banner(self.workspace_path)

        # Load TESS.md context
        tess_md_path = find_tess_md(self.workspace_path)
        tess_md_content = ""
        if tess_md_path:
            tess_md_content = read_tess_md(self.workspace_path)
            print_tess_md_loaded(tess_md_path)

        self._system_prompt = self._build_system_prompt(tess_md_content)

        # Interactive loop
        while True:
            try:
                user_input = console.input(get_code_prompt(self.workspace_path)).strip()
                if not user_input:
                    continue

                if user_input.lower() in ("exit", "quit", "q"):
                    print_success("Exited coding mode.")
                    break

                if user_input.lower() == "clear":
                    self.session_history = []
                    print_info("Session history cleared.")
                    continue

                # Run the agentic loop for this query
                self._run_agent_loop(user_input)

            except KeyboardInterrupt:
                print_info("\nInterrupted. Type 'exit' to leave coding mode.")
            except EOFError:
                break
            except Exception as e:
                print_error(f"Unexpected error: {e}")
                logger.error(e, exc_info=True)

    def _build_system_prompt(self, tess_md_content=""):
        """Construct the specialized coding system prompt."""
        # Get a compact workspace tree (first 30 entries)
        tree = self.tools.list_dir(".")
        tree_lines = tree.split('\n')[:30]
        tree_compact = '\n'.join(tree_lines)
        if len(tree.split('\n')) > 30:
            tree_compact += "\n... (more files)"

        prompt = (
            "You are TESS Coding Agent — an autonomous software engineer powered by AI. "
            "You are operating inside a terminal-based coding environment. "
            "You help the user understand, write, debug, refactor, and manage code. "
            "\n\n"
            f"WORKSPACE: {self.workspace_path}\n"
            f"OS: Windows (use PowerShell for commands)\n"
            "\n"
            f"WORKSPACE TREE:\n{tree_compact}\n"
            "\n"
        )

        if tess_md_content:
            prompt += (
                "PROJECT INSTRUCTIONS (from TESS.md):\n"
                f"{tess_md_content}\n\n"
            )

        prompt += TOOL_SCHEMA_DOC

        prompt += (
            "\n\nBEHAVIOR:\n"
            "- Be thorough: read files before editing, verify changes work.\n"
            "- Be concise in thoughts but detailed in code.\n"
            "- If the user asks a question that doesn't need tools, use 'done' immediately.\n"
            "- For multi-file changes, handle them one at a time.\n"
            "- After making edits, consider running tests or verifying the change.\n"
            "- NEVER fabricate file contents — always read first.\n"
            "\n"
            "ANALYSIS MODE (when user asks to 'analyse', 'review', 'audit', 'summarize', or 'explain'):\n"
            "- This is a READ-ONLY task. Do NOT use edit_file, write_file, or run_command.\n"
            "- Step 1 — Explore: use list_dir, read_file, file_outline, grep_search to understand the code.\n"
            "- Step 2 — Synthesize: once you have enough information, compose a structured Markdown analysis.\n"
            "- Step 3 — Save: use write_analysis(filename, content) to save your analysis as an .md file.\n"
            "  The filename should be descriptive, e.g. 'project_analysis.md' or 'code_review.md'.\n"
            "- Step 4 — Report: use done() to tell the user where the analysis file was saved and give a brief summary.\n"
            "- The analysis file MUST include: project overview, architecture/structure, key components, \n"
            "  dependencies, potential issues, and recommendations.\n"
        )

        return prompt

    def _run_agent_loop(self, user_query):
        """Execute the multi-step agentic tool loop for a single user query."""
        # Build messages for this turn
        messages = [{"role": "system", "content": self._system_prompt}]

        # Add session history for continuity
        for entry in self.session_history[-10:]:
            messages.append(entry)

        messages.append({"role": "user", "content": user_query})

        step = 0
        while step < MAX_AGENT_STEPS:
            step += 1
            print_step_count(step, MAX_AGENT_STEPS)
            print_thinking(f"Step {step}...")

            # Call the Brain for next action
            try:
                response_text = self.brain._call_api_with_retry(
                    messages, json_mode=True, temperature=0.4
                )
            except Exception as e:
                clear_thinking()
                print_error(f"LLM call failed: {e}")
                break

            clear_thinking()

            if not response_text:
                print_error("Brain returned empty response.")
                break

            # Parse the tool call
            try:
                action = self.brain._parse_json(response_text)
            except Exception as e:
                print_error(f"Failed to parse response: {e}")
                break

            # Handle non-dict responses (fallback to done)
            if not isinstance(action, dict):
                print_agent_message(str(action))
                break

            # If brain fell back to reply_op format, treat as done
            if action.get("action") in ("reply_op", "final_reply"):
                msg = action.get("content", str(action))
                print_agent_message(msg)
                self.session_history.append({"role": "user", "content": user_query})
                self.session_history.append({"role": "assistant", "content": msg})
                break

            thought = action.get("thought", "")
            tool = action.get("tool", "")
            args = action.get("args", {})

            if thought:
                print_thought(thought)

            # Handle 'done' tool
            if tool == "done":
                msg = args.get("message", "Done.")
                print_agent_message(msg)
                # Save to session history
                self.session_history.append({"role": "user", "content": user_query})
                self.session_history.append({"role": "assistant", "content": msg})
                break

            if not tool:
                # No tool specified — treat the whole response as a message
                content = action.get("content") or action.get("message") or response_text
                print_agent_message(str(content))
                break

            # Permission check
            if tool in DANGEROUS_TOOLS:
                from .config import Config
                if not Config.AUTONOMOUS_CODING:
                    if not ask_permission(tool, args):
                        # User denied
                        result = "Permission denied by user."
                        messages.append({"role": "assistant", "content": response_text})
                        messages.append({"role": "user", "content": f"Tool result: {result}"})
                        print_info("Permission denied.")
                        continue
                else:
                    # Inform user we are auto-executing
                    print_info("Auto-executing dangerous tool (Autonomous Mode)")

            # Execute the tool
            print_tool_call(tool, args)
            result = self._execute_tool(tool, args)
            print_tool_result(result, tool)

            # Feed result back to the LLM
            messages.append({"role": "assistant", "content": response_text})
            messages.append({"role": "user", "content": f"Tool result for {tool}:\n{result}"})

            time.sleep(0.3)  # Brief pause for readability

        else:
            print_error(f"Agent loop reached maximum steps ({MAX_AGENT_STEPS}).")

    def _execute_tool(self, tool, args):
        """Dispatch a tool call to the CodingTools methods."""
        try:
            if tool == "read_file":
                return self.tools.read_file(
                    args.get("path", ""),
                    args.get("start_line"),
                    args.get("end_line")
                )
            elif tool == "write_file":
                return self.tools.write_file(
                    args.get("path", ""),
                    args.get("content", "")
                )
            elif tool == "edit_file":
                return self.tools.edit_file(
                    args.get("path", ""),
                    args.get("search", ""),
                    args.get("replace", "")
                )
            elif tool == "list_dir":
                return self.tools.list_dir(args.get("path", "."))
            elif tool == "grep_search":
                return self.tools.grep_search(
                    args.get("pattern", ""),
                    args.get("path", "."),
                    args.get("extensions")
                )
            elif tool == "file_outline":
                return self.tools.file_outline(args.get("path", ""))
            elif tool == "run_command":
                return self.tools.run_command(
                    args.get("command", ""),
                    args.get("cwd")
                )
            elif tool == "git_status":
                return self.tools.git_status(args.get("path", "."))
            elif tool == "git_diff":
                return self.tools.git_diff(args.get("path", "."))
            elif tool == "git_commit":
                return self.tools.git_commit(
                    args.get("message", "Auto-commit by TESS"),
                    args.get("path", ".")
                )
            elif tool == "write_analysis":
                return self.tools.write_file(
                    args.get("filename", "analysis.md"),
                    args.get("content", "")
                )
            else:
                return f"Error: Unknown tool '{tool}'"
        except Exception as e:
            logger.error(f"Tool execution error: {e}", exc_info=True)
            return f"Error executing {tool}: {e}"
