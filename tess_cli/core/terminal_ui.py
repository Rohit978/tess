"""
TESS Terminal UI - Premium Visual Experience
Handles all terminal styling, banners, animations, and color output.
"""

import os
import sys
import time
import shutil

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
    """Print the main TESS banner."""
    w = get_width()
    print(f"\n{C.BRIGHT_BLACK}{'━' * w}{C.R}")
    print(BANNER)
    print(f"{C.BRIGHT_BLACK}{'━' * w}{C.R}")


def print_divider(char="─", color=C.BRIGHT_BLACK):
    w = get_width()
    print(f"{color}{char * w}{C.R}")


def animate_boot(text, delay=0.03):
    """Animated text typing effect."""
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    print()


def print_status(label, status, ok=True):
    """Print a status line like:  ✓ Module Name ........... ONLINE"""
    w = get_width()
    icon = f"{C.BRIGHT_GREEN}✓{C.R}" if ok else f"{C.BRIGHT_RED}✗{C.R}"
    dots_len = w - len(label) - len(status) - 8
    if dots_len < 3: dots_len = 3
    dots = f"{C.BRIGHT_BLACK}{'·' * dots_len}{C.R}"
    
    if ok:
        status_str = f"{C.BRIGHT_GREEN}{C.BOLD}{status}{C.R}"
    else:
        status_str = f"{C.BRIGHT_RED}{status}{C.R}"
    
    print(f"  {icon} {C.WHITE}{label}{C.R} {dots} {status_str}")


def boot_sequence(comps, config_data):
    """Print the full boot dashboard."""
    print()
    animate_boot(f"  {C.BRIGHT_CYAN}⚡ Initializing TESS Systems...{C.R}", delay=0.015)
    print()
    
    # Module status grid
    module_map = [
        ("Brain (LLM)", 'brain'),
        ("Security Engine", 'security'),
        ("App Launcher", 'launcher'),
        ("System Control", 'sys_ctrl'),
        ("File Manager", 'file_mgr'),
        ("Web Search", 'web_search'),
        ("Knowledge Base", 'knowledge_db'),
        ("Planner", 'planner'),
        ("YouTube Player", 'youtube_client'),
        ("WhatsApp", 'whatsapp'),
        ("Voice Client", 'voice_client'),
        ("Organizer", 'organizer'),
        ("Architect", 'architect'),
        ("Google Services", 'google_client'),
    ]
    
    for label, key in module_map:
        comp = comps.get(key)
        if comp is not None:
            print_status(label, "ONLINE")
        else:
            print_status(label, "OFFLINE", ok=False)
        time.sleep(0.04)  # Staggered animation
    
    print()


def print_provider_info(provider, model):
    """Print LLM provider info box."""
    print(f"  {C.BRIGHT_MAGENTA}🧠 LLM:{C.R} {C.BOLD}{C.WHITE}{provider.upper()}{C.R} {C.DIM}({model}){C.R}")


def print_ready():
    """Print the ready prompt header."""
    w = get_width()
    print(f"\n{C.BRIGHT_BLACK}{'━' * w}{C.R}")
    print(f"  {C.BRIGHT_GREEN}{C.BOLD}⚡ TESS IS ONLINE{C.R}  {C.DIM}Type 'exit' to quit · 'help' for commands{C.R}")
    print(f"{C.BRIGHT_BLACK}{'━' * w}{C.R}")


def get_prompt():
    """Return the styled user prompt string."""
    return f"\n{C.BRIGHT_CYAN}{C.BOLD}  ❯{C.R} "


def print_thinking():
    """Print thinking indicator."""
    print(f"  {C.BRIGHT_MAGENTA}◆{C.R} {C.DIM}Thinking...{C.R}", end="", flush=True)


def clear_thinking():
    """Clear the thinking line."""
    sys.stdout.write("\r" + " " * 40 + "\r")
    sys.stdout.flush()


def print_tess_message(msg):
    """Print a TESS response with styling."""
    print(f"\n  {C.BRIGHT_CYAN}◆ TESS:{C.R} {C.WHITE}{msg}{C.R}\n")


def print_tess_action(msg):
    """Print a TESS action notification."""
    print(f"  {C.BRIGHT_YELLOW}▸{C.R} {C.DIM}{msg}{C.R}")


def print_error(msg):
    """Print an error."""
    print(f"  {C.BRIGHT_RED}✗ ERROR:{C.R} {msg}")


def print_security_block(reason):
    """Print a security block warning."""
    print(f"\n  {C.BRIGHT_RED}{C.BOLD}🛡️  SECURITY BLOCK{C.R}")
    print(f"  {C.RED}{reason}{C.R}\n")


def print_warning(msg):
    """Print a warning."""
    print(f"  {C.BRIGHT_YELLOW}⚠{C.R} {C.YELLOW}{msg}{C.R}")


def print_success(msg):
    """Print a success message."""
    print(f"  {C.BRIGHT_GREEN}✓{C.R} {msg}")


def print_info(msg):
    """Print an info message."""
    print(f"  {C.BRIGHT_BLUE}ℹ{C.R} {C.DIM}{msg}{C.R}")


def print_goodbye():
    """Print exit message."""
    print(f"\n  {C.BRIGHT_MAGENTA}👋 TESS shutting down. See you later!{C.R}")
    print(f"  {C.DIM}Thank you for using TESS Terminal Pro{C.R}\n")


def print_help():
    """Display available commands."""
    print(f"""
  {C.BRIGHT_CYAN}{C.BOLD}━━━ TESS COMMANDS ━━━{C.R}

  {C.BRIGHT_WHITE}General{C.R}
  {C.CYAN}exit / quit{C.R}       {C.DIM}Shutdown TESS{C.R}
  {C.CYAN}help{C.R}              {C.DIM}Show this help menu{C.R}
  {C.CYAN}status{C.R}            {C.DIM}Show module status{C.R}

  {C.BRIGHT_WHITE}Learning{C.R}
  {C.CYAN}learn apps{C.R}        {C.DIM}Scan installed applications{C.R}
  {C.CYAN}learn commands{C.R}    {C.DIM}Index system commands{C.R}
  {C.CYAN}watch <path>{C.R}      {C.DIM}Watch a directory for learning{C.R}

  {C.BRIGHT_WHITE}Voice{C.R}
  {C.CYAN}listen / voice{C.R}    {C.DIM}Start voice input{C.R}

  {C.BRIGHT_WHITE}Features{C.R}
  {C.DIM}Just type naturally! Examples:{C.R}
  {C.WHITE}  "play lofi beats on youtube"{C.R}
  {C.WHITE}  "send Hi to Mom on whatsapp"{C.R}
  {C.WHITE}  "open notepad"{C.R}
  {C.WHITE}  "list files on desktop"{C.R}
  {C.WHITE}  "search for python tutorials"{C.R}
  {C.WHITE}  "organize my downloads folder"{C.R}
""")
