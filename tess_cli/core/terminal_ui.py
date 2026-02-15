import os
import sys
import time
import shutil
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.live import Live
from rich.table import Table
from rich.theme import Theme

# Initialize Rich Console with a custom theme
custom_theme = Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "red",
    "success": "green",
    "tess": "bright_magenta",
    "user": "bright_cyan"
})
console = Console(theme=custom_theme)

# ─── ANSI Color Codes ────────────────────────────────────────────────────────

class C:
    """Color constants using ANSI escape codes."""
    # Reset
    R = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    ITALIC = "\033[3m"
    UNDERLINE = "\033[4m"
    BLINK = "\033[5m"
    
    # Foreground
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    
    # Bright Foreground
    BRIGHT_BLACK = "\033[90m"
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"
    
    # Background
    BG_BLACK = "\033[40m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_BLUE = "\033[44m"
    BG_MAGENTA = "\033[45m"
    BG_CYAN = "\033[46m"


def enable_ansi():
    """Enable ANSI escape codes on Windows."""
    if sys.platform == "win32":
        os.system("")  # Enables ANSI on Windows 10+
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        except:
            pass

enable_ansi()

# ─── Terminal Width ───────────────────────────────────────────────────────────

def get_width():
    try:
        return shutil.get_terminal_size().columns
    except:
        return 80

# ─── Banner ───────────────────────────────────────────────────────────────────

BANNER = f"""{C.BRIGHT_CYAN}{C.BOLD}
  ████████╗███████╗███████╗███████╗
  ╚══██╔══╝██╔════╝██╔════╝██╔════╝
     ██║   █████╗  ███████╗███████╗
     ██║   ██╔══╝  ╚════██║╚════██║
     ██║   ███████╗███████║███████║
     ╚═╝   ╚══════╝╚══════╝╚══════╝{C.R}
  {C.DIM}{C.BRIGHT_MAGENTA}Terminal Executive Support System{C.R}  {C.DIM}v5.0{C.R}
"""

MINI_BANNER = f"""{C.BRIGHT_CYAN}{C.BOLD}  ▀▀█▀▀ █▀▀ █▀▀ █▀▀
    █   █▀▀ ▀▀█ ▀▀█
    ▀   ▀▀▀ ▀▀▀ ▀▀▀{C.R}  {C.DIM}v5.0{C.R}"""


# ─── Styled Output Functions ─────────────────────────────────────────────────

def print_banner():
    """Print the main TESS banner using rich."""
    banner_text = Text(BANNER, style="bright_cyan bold")
    console.print(Panel(banner_text, subtitle="[dim]v5.0 - Agentic Developer Edition[/dim]", border_style="bright_magenta", expand=False))

def print_thinking(msg="Thinking..."):
    """Print thinking indicator using rich spinner."""
    # We'll use a globally stored progress object for the thinking line
    global _thinking_spinner
    _thinking_spinner = Progress(
        SpinnerColumn("dots", style="bright_magenta"),
        TextColumn("[magenta]{task.description}"),
        transient=True,
        console=console
    )
    _thinking_spinner.start()
    _thinking_spinner.add_task(description=msg)

def clear_thinking():
    """Clear the thinking line."""
    global _thinking_spinner
    if '_thinking_spinner' in globals() and _thinking_spinner:
        _thinking_spinner.stop()

def print_tess_message(msg):
    """Print a TESS response with rich styling."""
    console.print(f"\n[tess]◆ TESS:[/tess] {msg}", highlight=True)

def print_tess_action(msg):
    """Print a TESS action notification."""
    console.print(f"  [yellow]▸[/yellow] [dim]{msg}[/dim]")

def print_plan(steps):
    """Print an agent's execution plan."""
    table = Table(title="AGENT PLAN", border_style="bright_magenta", show_lines=True)
    table.add_column("#", style="dim", width=2)
    table.add_column("Step", style="white")
    
    for i, step in enumerate(steps, 1):
        table.add_row(str(i), step)
    
    console.print(Panel(table, border_style="bright_magenta"))


def print_error(msg):
    """Print an error using rich."""
    console.print(f"  [error]✗ ERROR:[/error] {msg}")

def print_security_block(reason):
    """Print a security block warning using rich."""
    console.print(Panel(f"[error]{reason}[/error]", title="🛡️ SECURITY BLOCK", border_style="red"))

def print_warning(msg):
    """Print a warning using rich."""
    console.print(f"  [warning]⚠[/warning] {msg}")

def print_success(msg):
    """Print a success message using rich."""
    console.print(f"  [success]✓[/success] {msg}")

def print_info(msg):
    """Print an info message using rich."""
    console.print(f"  [info]ℹ[/info] [dim]{msg}[/dim]")


def print_greeting(greeting, extras=""):
    """Print the personalized greeting."""
    print(f"\n  {C.BRIGHT_WHITE}{C.BOLD}{greeting}{C.R}")
    if extras:
        print(f"  {C.DIM}{extras}{C.R}")


def print_stats_dashboard(stats):
    """Print user engagement statistics."""
    w = 40
    print(f"\n  {C.BRIGHT_MAGENTA}┏{'━' * (w-2)}┓{C.R}")
    print(f"  {C.BRIGHT_MAGENTA}┃{C.R} {C.BOLD}SESSION STATS{C.R} {' ' * (w-17)} {C.BRIGHT_MAGENTA}┃{C.R}")
    print(f"  {C.BRIGHT_MAGENTA}┠{'─' * (w-2)}┨{C.R}")
    
    lines = [
        (f"Sessions", f"{stats['sessions']}"),
        (f"Commands", f"{stats['commands']}"),
        (f"Streak", f"{stats['streak']} days 🔥"),
        (f"Best", f"{stats['best_streak']} days")
    ]
    
    for label, val in lines:
        padding = w - len(label) - len(val) - 4
        print(f"  {C.BRIGHT_MAGENTA}┃{C.R} {C.CYAN}{label}:{C.R}{' ' * padding}{C.WHITE}{val}{C.R} {C.BRIGHT_MAGENTA}┃{C.R}")
    
    print(f"  {C.BRIGHT_MAGENTA}┗{'━' * (w-2)}┛{C.R}")


def print_goodbye(name=None):
    """Print exit message."""
    who = name or "there"
    print(f"\n  {C.BRIGHT_MAGENTA}👋 See you later, {who}!{C.R}")
    print(f"  {C.DIM}Thank you for using TESS Terminal Pro{C.R}\n")


def print_fact_learned(facts):
    """Print when TESS learns a new fact."""
    for fact in facts:
        print(f"  {C.BRIGHT_GREEN}🧠 Learned:{C.R} {C.DIM}{fact}{C.R}")



def print_help():
    """Display available commands using a rich table."""
    table = Table(title="TESS COMMANDS", border_style="bright_cyan", show_header=True, header_style="bold white")
    table.add_column("Category", style="dim")
    table.add_column("Command", style="cyan")
    table.add_column("Description", style="white")
    
    table.add_row("General", "exit / quit", "Shutdown TESS")
    table.add_row("", "help", "Show this help menu")
    table.add_row("", "status", "Show module status")
    
    table.add_row("Learning", "learn apps", "Scan installed applications")
    table.add_row("", "learn commands", "Index system commands")
    table.add_row("", "watch <path>", "Watch a directory for learning")
    
    table.add_row("Voice", "listen / voice", "Start voice input")
    
    table.add_row("Coding", "ls / analyze", "List and analyze the project")
    table.add_row("", "grep <pattern>", "Search for text in files")
    table.add_row("", "outline <file>", "Get the structure of a file")
    
    console.print(table)
    console.print("[dim]Just type naturally for everything else! Example: 'make a todo app'[/dim]")
