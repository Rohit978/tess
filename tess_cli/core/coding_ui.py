"""
TESS Coding Mode UI — Rich terminal components for the coding agent.
"""

import os
import sys
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text
from rich.table import Table
from rich.markdown import Markdown

console = Console()

# ─── Color Palette ────────────────────────────────────────────────────────────
ACCENT = "cyan"
TOOL_COLOR = "bright_magenta"
SUCCESS = "bright_green"
WARN = "bright_yellow"
ERR = "bright_red"
DIM = "dim"

CODING_BANNER = r"""
  ╔══════════════════════════════════════════╗
  ║     ⚡ TESS  CODING  MODE ⚡            ║
  ║                                          ║
  ╚══════════════════════════════════════════╝
"""


def print_code_banner(workspace_path):
    """Print the coding mode entry banner."""
    console.print(CODING_BANNER, style=f"bold {ACCENT}")
    console.print(f"  📂 Workspace: [bold]{workspace_path}[/bold]", style=ACCENT)
    console.print(f"  💡 Type your coding task. Type [bold]exit[/bold] or [bold]quit[/bold] to leave.\n", style=DIM)


def get_code_prompt(cwd):
    """Return the coding mode prompt string showing cwd."""
    short = os.path.basename(cwd) or cwd
    return f"[bold {ACCENT}]tess:code[/bold {ACCENT}] [dim]{short}[/dim] [bold {ACCENT}]>[/bold {ACCENT}] "


def print_thinking(msg="Thinking..."):
    """Show a thinking indicator."""
    console.print(f"  🧠 [dim italic]{msg}[/dim italic]", end="\r")


def clear_thinking():
    """Clear the thinking line."""
    console.print(" " * 80, end="\r")


def print_thought(thought):
    """Display the agent's internal reasoning."""
    if thought:
        console.print(f"  💭 [dim italic]{thought}[/dim italic]")


def print_tool_call(tool, args):
    """Display what tool is being invoked."""
    # Build a compact arg summary
    arg_parts = []
    for k, v in (args or {}).items():
        val = str(v)
        if len(val) > 60:
            val = val[:57] + "..."
        arg_parts.append(f"{k}={val}")
    arg_str = ", ".join(arg_parts) if arg_parts else ""

    console.print(f"\n  🔧 [bold {TOOL_COLOR}]{tool}[/bold {TOOL_COLOR}]({arg_str})", highlight=False)


def print_tool_result(result, tool_name=""):
    """Display tool output, with syntax highlighting for code."""
    if not result:
        result = "(empty)"

    lines = result.strip().split('\n')
    truncated = len(lines) > 40
    display = '\n'.join(lines[:40])
    if truncated:
        display += f"\n... ({len(lines) - 40} more lines)"

    # Detect if it looks like code output
    if tool_name in ("read_file", "git_diff"):
        console.print(Panel(
            display,
            title=f"[dim]Result[/dim]",
            border_style="dim",
            padding=(0, 1),
            expand=False
        ))
    else:
        console.print(f"  [dim]→ {display}[/dim]", highlight=False)


def print_permission_prompt(tool, args):
    """Display a permission request for a dangerous operation."""
    console.print()
    console.print(Panel(
        f"[bold]Tool:[/bold] {tool}\n[bold]Args:[/bold] {args}",
        title="⚠️  Permission Required",
        border_style=WARN,
        padding=(0, 1),
    ))


def ask_permission(tool, args):
    """Ask user for permission. Returns True if approved."""
    print_permission_prompt(tool, args)
    try:
        answer = console.input(f"  [bold {WARN}]Allow? (Y/n):[/bold {WARN}] ").strip().lower()
        return answer in ('', 'y', 'yes', 'ok')
    except (EOFError, KeyboardInterrupt):
        return False


def print_agent_message(msg):
    """Print the agent's final response."""
    console.print()
    console.print(Panel(
        Markdown(msg),
        title="[bold]TESS[/bold]",
        border_style=ACCENT,
        padding=(1, 2),
    ))
    console.print()


def print_error(msg):
    """Print an error message."""
    console.print(f"  ❌ [bold {ERR}]{msg}[/bold {ERR}]")


def print_success(msg):
    """Print a success message."""
    console.print(f"  ✅ [bold {SUCCESS}]{msg}[/bold {SUCCESS}]")


def print_info(msg):
    """Print an info message."""
    console.print(f"  ℹ️  [{DIM}]{msg}[/{DIM}]")


def print_tess_md_loaded(path):
    """Notify user that TESS.md was loaded."""
    console.print(f"  📋 Loaded project context from [bold]{os.path.basename(path)}[/bold]", style=ACCENT)


def print_step_count(step, max_steps):
    """Show current step in the agent loop."""
    console.print(f"  [dim]Step {step}/{max_steps}[/dim]", end="\r")
