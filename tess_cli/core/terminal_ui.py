import os
import sys
import time
import shutil
import random
from .config import Config

from rich.console import Console



from rich.panel import Panel
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
from rich.live import Live
from rich.table import Table
from rich.theme import Theme
from rich import box
from rich.layout import Layout
from rich.align import Align

# Initialize Rich Console with a Cyberpunk Theme
custom_theme = Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "bold red",
    "success": "bold green",
    "tess": "bold magenta",
    "user": "bold cyan",
    "dim": "dim white",
    "border": "magenta"
})
console = Console(theme=custom_theme)

# ─── Color Constants ──────────────────────────────────────────────────────────

class ColorMeta(type):
    def __getattr__(cls, name):
        # Fallback to white for any missing color attributes
        return "\033[37m"

class C(metaclass=ColorMeta):
    R = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    
    # Standard Colors
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    
    # Bright Colors
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"




def get_width():
    try:
        return shutil.get_terminal_size().columns
    except:
        return 80

# ─── Visual Components ───────────────────────────────────────────────────────

def make_gradient(text, start_color=(0, 255, 255), end_color=(255, 0, 255)):
    """Simulate a gradient by interpolating colors (Placeholder for simple rich styles to keep it fast)."""
    # For a CLI, true gradients are heavy. We'll use a rich style map instead.
    return Text(text, style="bright_cyan")

BANNER_TEXT = """
  ████████╗███████╗███████╗███████╗
  ╚══██╔══╝██╔════╝██╔════╝██╔════╝
     ██║   █████╗  ███████╗███████╗
     ██║   ██╔══╝  ╚════██║╚════██║
     ██║   ███████╗███████║███████║
     ╚═╝   ╚══════╝╚══════╝╚══════╝
"""

def print_banner():
    """Print the cyber-styled banner."""
    # Create a gradient effect using Rich Text
    banner = Text(BANNER_TEXT)
    banner.stylize("bright_cyan", 0, 100)
    banner.stylize("magenta", 100, 200) # Simple split gradient
    
    # Subtitle
    subtitle = Text("Terminal Executive Support System v5.0", style="dim italic white")
    
    # Container
    panel = Panel(
        Align.center(banner + "\n" + str(subtitle)),
        border_style="bright_magenta",
        box=box.HEAVY,
        subtitle="[bold cyan]AGENTIC CORE ONLINE[/bold cyan]",
        subtitle_align="right"
    )
    console.print(panel)

def print_divider():
    console.print(f"[dim magenta]{'─' * get_width()}[/dim magenta]")

# ─── Boot Animation ──────────────────────────────────────────────────────────

def boot_sequence(components, config_data):
    """
    Live Animated Boot Sequence.
    """
    console.print("\n[bold cyan]⚡ INITIALIZING TESS CORE...[/bold cyan]\n")
    
    job_progress = Progress(
        "{task.description}",
        SpinnerColumn("dots", style="magenta"),
        BarColumn(bar_width=None, style="dim magenta", complete_style="cyan"),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        expand=True
    )
    
    # Create tasks
    tasks = {
        "brain": job_progress.add_task("[cyan]Connecting Neural Pathways...", total=100),
        "memory": job_progress.add_task("[magenta]Loading Vector Database...", total=100),
        "security": job_progress.add_task("[green]Engaging Security Protocols...", total=100),
        "tools": job_progress.add_task("[yellow]Registering Agent Tools...", total=100)
    }
    
    with Live(Panel(job_progress, title="SYSTEM BOOT", border_style="magenta", box=box.ROUNDED), refresh_per_second=10):
        while not job_progress.finished:
            for task_id in tasks.values():
                advance = random.randint(1, 5)
                job_progress.advance(task_id, advance)
            time.sleep(0.05)

    # Final "Online" Table
    print_status_dashboard(components)

def print_status_dashboard(components):
    """Static status table after boot."""
    table = Table(box=box.SIMPLE_HEAD, border_style="dim magenta", expand=True)
    table.add_column("COMPONENT", style="cyan bold")
    table.add_column("STATUS", style="white")
    table.add_column("LATENCY", style="dim")
    
    # Simulated statuses
    core_comps = [('Brain Engine', 'ONLINE', '12ms'), ('Memory Bank', 'ONLINE', '4ms'), 
                  ('Security', 'ACTIVE', '0ms'), ('Executor', 'READY', '0ms')]
                  
    for name, status, lat in core_comps:
        color = "green" if status == "ONLINE" or status == "ACTIVE" else "yellow"
        table.add_row(name, f"[{color}]● {status}[/{color}]", lat)
        
    console.print(Panel(table, title="[bold]SYSTEM METRICS[/bold]", border_style="dim white"))

# ─── Chat Interface ──────────────────────────────────────────────────────────

def get_prompt():
    """Cyberpunk prompt."""
    return f"\n[bold bright_cyan]❯[/bold bright_cyan] [bold white]USER[/bold white] [dim]>>[/dim] "

_thinking_spinner = None

def print_thinking(msg="Thinking..."):
    global _thinking_spinner
    
    clear_thinking() # Ensure any previous spinner is cleanly stopped
    
    _thinking_spinner = Progress(
        SpinnerColumn("aesthetic", style="bright_magenta"),
        TextColumn("[italic magenta]{task.description}"),
        transient=True,
        console=console
    )
    _thinking_spinner.start()
    _thinking_spinner.add_task(description=msg)

def clear_thinking():
    global _thinking_spinner
    if '_thinking_spinner' in globals() and _thinking_spinner:
        _thinking_spinner.stop()

def print_thought(msg):
    """
    Simulates TESS's 'inner monologue' in a subtle, dim style.
    """
    console.print(f"  [dim italic magenta]💭 {msg}[/dim italic magenta]")

def print_tess_message(msg):
    """
    Render TESS response in a softer, more conversational style.
    """
    # Use a simpler, non-heavy box for a 'softer' feel
    panel = Panel(
        Text(msg),
        title="[bold magenta]◆ TESS[/bold magenta]",
        title_align="left",
        border_style="magenta",
        box=box.SIMPLE,
        padding=(1, 1)
    )
    console.print(panel)

def print_tess_action(msg):
    if Config.get_ui_mode() == "minimal":
        return
    console.print(f"  [bold yellow]⚡ ACTION:[/bold yellow] [dim]{msg}[/dim]")

def print_error(msg):
    console.print(f"  [bold red]⛔ SYSTEM ERROR:[/bold red] {msg}")

def print_warning(msg):
    console.print(f"  [bold yellow]⚠ WARNING:[/bold yellow] {msg}")

def print_success(msg):
    console.print(f"  [bold green]✓ SUCCESS:[/bold green] {msg}")

def print_info(msg):
    console.print(f"  [bold cyan]ℹ INFO:[/bold cyan] {msg}")

def print_security_block(reason):
    console.print(Panel(f"[bold red]Create an implementation plan first![/bold red]\nReason: {reason}", title="🛡️ SECURITY BLOCK", border_style="red", box=box.HEAVY))

# ─── Legacy Wrappers (For compatibility) ─────────────────────────────────────

def animate_boot(msg, delay=0.02):
    # Backward compatibility for simple prints
    console.print(msg)

def print_status(comp_name, status):
    pass # Handled by boot_sequence now

def print_provider_info(provider, model):
    console.print(f"[dim]  running on[/dim] [bold magenta]{provider.upper()}[/bold magenta]:[cyan]{model}[/cyan]")

def print_ready():
    console.print(Align.center("[bold green]SYSTEM READY. WAITING FOR INPUT...[/bold green]"))

def print_greeting(greeting, extras=""):
    console.print(f"\n  [italic white]{greeting}[/italic white]")
    if extras: console.print(f"  [dim]{extras}[/dim]")

def print_stats_dashboard(stats):
    pass # Integrated into boot

def print_help():
    """Display available commands using a rich table."""
    table = Table(title="TESS COMMANDS", border_style="bright_cyan", show_header=True, header_style="bold white", expand=True)
    table.add_column("Category", style="dim cyan", width=12)
    table.add_column("Command / Trigger", style="white bold", width=25)
    table.add_column("Description & Examples", style="dim white")
    
    # Setup & Config
    table.add_row("Setup", "learn apps", "Index installed apps (Run once)")
    table.add_row("", "learn commands", "Index system commands (Run once)")
    table.add_row("", "watch <path>", "Switch project context to new folder")
    
    # System
    table.add_row("System", "exit / quit", "Shutdown TESS")
    table.add_row("", "persona <name>", "Switch personality: [i]persona cute[/i]")
    table.add_row("", "status", "Show module status dashboard")
    
    # Coding
    table.add_row("Coding", "ls / analyse", "List files or analyze current directory structure")
    table.add_row("", "grep <pattern>", "Search text in files: [i]grep TODO .[/i]")
    table.add_row("", "outline <file>", "Show classes/methods in a file")
    
    # Git
    table.add_row("Git", "git status / log", "Check repo status or commit history")
    table.add_row("", "commit / push", "Natural language git: [i]\"commit with message 'fix bug'\"[/i]")
    
    # General
    table.add_row("General", "Natural Language", "Just ask! Examples:\n• [i]\"Check the github version\"[/i]\n• [i]\"Open Spotify and play LoFi\"[/i]\n• [i]\"Create a python script to parse CSV\"[/i]")
    
    console.print(table)

def print_goodbye(name="User"):
    console.print(f"\n[bold magenta]👋 Shutting down... Goodbye, {name}![/bold magenta]")

def print_fact_learned(facts):
    for f in facts:
        console.print(f"  [dim cyan]🧠 Memory Updated:[/dim cyan] {f}")

def print_cognitive_flow(query, layer, details=None):
    """
    Renders a stunning terminal-based flowchart of TESS's cognitive routing decision.
    Shows the active layer, processing speed, and execution path.
    """
    if Config.get_ui_mode() == "minimal":
        return
        
    title = "[bold magenta]◆ COGNITIVE PATHWAY VISUALIZER[/bold magenta]"
    
    # Layer specific styling
    if layer == "reflex":
        layer_display = "[bold green]REFLEX LAYER (Deterministic Bypass)[/bold green]"
        speed = "⚡ <1ms [Instant]"
        flow_path = "[cyan]User Query[/cyan] ──▶ [magenta]Cognitive Router[/magenta] ──▶ [green]ReflexBrain[/green] ──▶ [yellow]Direct OS Action[/yellow]"
        extra_info = "LLM inference skipped entirely. Direct execution pattern matched."
    elif layer == "habit":
        layer_display = "[bold bright_cyan]HABIT LAYER (Cached Procedural Skill)[/bold bright_cyan]"
        speed = "⚡ <1ms [Compiled]"
        flow_path = "[cyan]User Query[/cyan] ──▶ [magenta]Cognitive Router[/magenta] ──▶ [bright_cyan]HabitBrain[/bright_cyan] ──▶ [yellow]Compiled Skill Graph[/yellow]"
        
        habit_name = details.get("name") if isinstance(details, dict) else "unknown"
        steps_count = len(details.get("steps", [])) if isinstance(details, dict) else 0
        extra_info = f"Executing cached workflow graph: [bold magenta]'{habit_name}'[/bold magenta] ({steps_count} pre-compiled steps)."
    elif layer == "planner":
        layer_display = "[bold bright_magenta]PLANNER LAYER (Strategic Decomposition)[/bold bright_magenta]"
        speed = "🐢 1.5s - 3.5s [Agentic Loops]"
        flow_path = "[cyan]User Query[/cyan] ──▶ [magenta]Cognitive Router[/magenta] ──▶ [bright_magenta]PlannerBrain[/bright_magenta] ──▶ [yellow]Task Registry & Agent Loop[/yellow]"
        extra_info = "Loaded structured user profile facts + semantic vector database context."
    else: # reasoner
        layer_display = "[bold yellow]DEEP REASONER LAYER (Conversational & Complex)[/bold yellow]"
        speed = "🐢 2.0s - 4.5s [Deep Thought]"
        flow_path = "[cyan]User Query[/cyan] ──▶ [magenta]Cognitive Router[/magenta] ──▶ [yellow]TaskBrain[/yellow] ──▶ [bright_magenta]LLM Reasoning Core[/bright_magenta]"
        extra_info = "Engaging core thinking pathways with episodic context loading and active safety validation."

    # Assemble visual table or panel
    table = Table(box=box.SIMPLE, show_header=False, expand=True)
    table.add_row("[bold white]Query:[/bold white]", f"[dim italic]\"{query}\"[/dim italic]")
    table.add_row("[bold white]Active Brain:[/bold white]", layer_display)
    table.add_row("[bold white]Cognitive Latency:[/bold white]", speed)
    table.add_row("[bold white]Information Flow:[/bold white]", flow_path)
    if extra_info:
        table.add_row("[bold white]Diagnostics:[/bold white]", f"[dim]{extra_info}[/dim]")

    panel = Panel(
        table,
        title=title,
        title_align="left",
        border_style="magenta",
        box=box.ROUNDED,
        padding=(0, 1)
    )
    console.print(panel)
