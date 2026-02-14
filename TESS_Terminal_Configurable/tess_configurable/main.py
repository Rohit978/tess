#!/usr/bin/env python3
"""
TESS Terminal - Configurable Edition
Main entry point
"""

import sys
import os
import argparse
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    from rich.live import Live
    from rich.spinner import Spinner
    from rich.prompt import Prompt, Confirm
    from rich.layout import Layout
except ImportError:
    print("Installing required dependencies...")
    os.system(f"{sys.executable} -m pip install rich -q")
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    from rich.live import Live
    from rich.spinner import Spinner
    from rich.prompt import Prompt, Confirm

from tess_configurable.config_manager import get_config_manager
from tess_configurable.setup_wizard import run_setup
from tess_configurable.settings_menu import open_settings
from tess_configurable.core.brain import Brain
from tess_configurable.core.orchestrator import Orchestrator


console = Console()


class TessTerminal:
    """
    Main TESS Terminal application.
    """
    
    def __init__(self):
        self.config_mgr = get_config_manager()
        self.config = self.config_mgr.config
        self.brain: Brain = None
        self.orchestrator: Orchestrator = None
        self.running = True
        
    def initialize(self) -> bool:
        """Initialize TESS components."""
        # Check if configured
        if not self.config_mgr.is_configured():
            console.print("[yellow]⚠ TESS is not configured yet.[/yellow]")
            if Confirm.ask("Run setup wizard?"):
                if not run_setup():
                    return False
            else:
                return False
        
        # Initialize brain
        try:
            self.brain = Brain(user_id="default")
            self.orchestrator = Orchestrator(self.config)
            
            # Start Telegram Bot if enabled
            if self.config.features.telegram_bot and self.config.telegram.bot_token:
                try:
                    from tess_configurable.interfaces.telegram_bot import TessBot
                    import threading
                    
                    self.telegram_bot = TessBot(self.brain, self.orchestrator)
                    
                    # Run in daemon thread
                    t = threading.Thread(target=self.telegram_bot.run, daemon=True)
                    t.start()
                    console.print("[green]Telegram Bot started (background)[/green]")
                except Exception as e:
                    console.print(f"[red]Failed to start Telegram Bot: {e}[/red]")
            
            return True
        except Exception as e:
            console.print(f"[red]Failed to initialize: {e}[/red]")
            return False
    
    def run(self):
        """Main interactive loop."""
        self._show_welcome()
        
        while self.running:
            try:
                # Get user input
                user_input = Prompt.ask("\n[bold cyan]You[/bold cyan]")
                
                if not user_input.strip():
                    continue
                
                # Handle special commands
                if self._handle_special_command(user_input):
                    continue
                
                # Process through brain
                with console.status("[bold green]Thinking...[/bold green]"):
                    action = self.brain.generate_command(user_input)
                
                # Execute action
                self._execute_action(action)
                
            except KeyboardInterrupt:
                console.print("\n[yellow]Use 'exit' or 'quit' to exit.[/yellow]")
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
    
    def run_single(self, command: str):
        """Execute a single command and exit."""
        if not self.initialize():
            sys.exit(1)
        
        console.print(f"[dim]Command: {command}[/dim]\n")
        
        with console.status("[bold green]Processing...[/bold green]"):
            action = self.brain.generate_command(command)
        
        self._execute_action(action)
    
    def _show_welcome(self):
        """Display welcome banner."""
        # Get current provider info
        provider = self.config.llm.provider.upper()
        model = self.config.llm.model
        
        welcome_text = Text()
        welcome_text.append("┌─────────────────────────────────┐\n", style="cyan")
        welcome_text.append("│     ", style="cyan")
        welcome_text.append("TESS Terminal", style="bold cyan")
        welcome_text.append("          │\n", style="cyan")
        welcome_text.append("│     ", style="cyan");
        welcome_text.append("Configurable Edition", style="dim")
        welcome_text.append("  │\n", style="cyan")
        welcome_text.append("├─────────────────────────────────┤\n", style="cyan")
        welcome_text.append(f"│  Provider: {provider:19} │\n", style="green")
        welcome_text.append(f"│  Model: {model[:23]:23} │\n", style="green")
        welcome_text.append(f"│  Security: {self.config.security.level:16} │\n", style="yellow")
        welcome_text.append("└─────────────────────────────────┘", style="cyan")
        
        console.print(welcome_text)
        console.print("\n[dim]Type 'help' for commands, 'exit' to quit[/dim]\n")
    
    def _handle_special_command(self, user_input: str) -> bool:
        """
        Handle special CLI commands.
        Returns True if command was handled.
        """
        cmd = user_input.lower().strip()
        
        if cmd in ["exit", "quit", "q"]:
            console.print("[yellow]Goodbye! 👋[/yellow]")
            self.running = False
            return True
        
        if cmd in ["help", "h", "?"]:
            self._show_help()
            return True
        
        if cmd == "clear":
            console.clear()
            self._show_welcome()
            return True
        
        if cmd == "config":
            open_settings()
            # Reload config
            self.config_mgr.load()
            self.config = self.config_mgr.config
            self.brain = Brain(user_id="default")
            self.orchestrator = Orchestrator(self.config)
            return True
        
        if cmd == "history":
            self._show_history()
            return True
        
        if cmd == "status":
            self._show_status()
            return True
        
        if cmd.startswith("!"):
            # Direct shell command
            shell_cmd = user_input[1:].strip()
            result = self.orchestrator.executor.execute_command(shell_cmd)
            console.print(f"[dim]{result}[/dim]")
            return True
        
        return False
    
    def _execute_action(self, action: dict):
        """Execute an action and display results."""
        action_type = action.get("action", "error")
        
        if action_type == "error":
            console.print(f"[red]Error: {action.get('reason', 'Unknown error')}[/red]")
            return
        
        # Show action being taken
        reason = action.get("reason", "")
        if reason:
            console.print(f"[dim]Reason: {reason}[/dim]")
        
        # Execute
        result = self.orchestrator.process_action(action, output_callback=console.print)
        
        # Update brain history
        self.brain.update_history("system", f"Executed {action_type}: {result[:100]}")
    
    def _show_help(self):
        """Display help information."""
        help_text = """
[bold cyan]TESS Terminal Commands[/bold cyan]

[bold]Special Commands:[/bold]
  [cyan]help[/cyan]        Show this help message
  [cyan]clear[/cyan]       Clear the screen
  [cyan]config[/cyan]      Open settings menu
  [cyan]history[/cyan]     Show conversation history
  [cyan]status[/cyan]      Show system status
  [cyan]exit/quit[/cyan]   Exit TESS
  [cyan]![command][/cyan]  Execute shell command directly

[bold]Action Types:[/bold]
  • Launch apps: [dim]"Open Chrome"[/dim]
  • Execute commands: [dim]"List files"[/dim]
  • File operations: [dim]"Read myfile.txt"[/dim]
  • System control: [dim]"Take screenshot"[/dim]
  • Web search: [dim]"Search for Python docs"[/dim]
  • General chat: [dim]"How are you?"[/dim]

[bold]Tips:[/bold]
  • Use natural language - TESS understands context
  • Type 'config' anytime to change settings
  • Security level affects command confirmation
        """
        console.print(help_text)
    
    def _show_history(self):
        """Display conversation history."""
        if not self.brain.history:
            console.print("[dim]No conversation history yet.[/dim]")
            return
        
        console.print("\n[bold]Conversation History[/bold]\n")
        for msg in self.brain.history[-10:]:  # Last 10
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            
            if role == "user":
                console.print(f"[cyan]You:[/cyan] {content[:100]}")
            elif role == "assistant":
                console.print(f"[green]TESS:[/green] {content[:100]}...")
            else:
                console.print(f"[dim]{role}:[/dim] {content[:100]}")
    
    def _show_status(self):
        """Display system status."""
        table = Panel(
            f"""[bold]Configuration Status[/bold]
            
[cyan]LLM Provider:[/cyan] {self.config.llm.provider.upper()}
[cyan]Model:[/cyan] {self.config.llm.model}
[cyan]API Keys:[/cyan] {len(self.config.llm.api_keys)} configured

[cyan]Security Level:[/cyan] {self.config.security.level}
[cyan]Safe Mode:[/cyan] {'Enabled' if self.config.security.safe_mode else 'Disabled'}

[cyan]Features:[/cyan]
  Voice: {'✓' if self.config.features.voice_input else '✗'}
  Web Search: {'✓' if self.config.features.web_search else '✗'}
  Telegram: {'✓' if self.config.features.telegram_bot else '✗'}

[dim]Config file: {self.config_mgr.config_file}[/dim]""",
            title="System Status",
            border_style="cyan"
        )
        console.print(table)


def main():
    """Main entry point."""
    # Fix common typos: -setup → --setup, -settings → --settings, etc.
    for i, arg in enumerate(sys.argv[1:], 1):
        if arg in ('-setup', '-s'):
            sys.argv[i] = '--setup'
        elif arg in ('-settings', '-c'):
            sys.argv[i] = '--settings'
        elif arg in ('-reset', '-r'):
            sys.argv[i] = '--reset'
        elif arg in ('-version', '-v'):
            sys.argv[i] = '--version'
        elif arg in ('-help', '-h'):
            sys.argv[i] = '--help'
        elif arg in ('-google-setup', '-g'):
            sys.argv[i] = '--google-setup'
        elif arg in ('-notion-setup', '-n'):
            sys.argv[i] = '--notion-setup'
        elif arg in ('-telegram-setup', '-t'):
            sys.argv[i] = '--telegram-setup'
    
    parser = argparse.ArgumentParser(
        description="TESS Terminal - Configurable AI Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  tess                    Start interactive mode
  tess --setup            Run first-time setup (also: -setup)
  tess --settings         Open settings menu (also: -settings)
  tess --google-setup     Setup Gmail and Calendar
  tess --notion-setup     Setup Notion integration
  tess --telegram-setup   Setup Telegram bot
  tess "read my emails"   Execute single command
  tess --version          Show version (also: -version)
        """
    )
    
    parser.add_argument(
        "command",
        nargs="?",
        help="Command to execute (if not provided, enters interactive mode)"
    )
    
    parser.add_argument(
        "--setup",
        action="store_true",
        help="Run setup wizard"
    )
    
    parser.add_argument(
        "--settings",
        action="store_true",
        help="Open settings menu"
    )
    
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset configuration to defaults"
    )
    
    parser.add_argument(
        "--version",
        action="store_true",
        help="Show version"
    )
    
    parser.add_argument(
        "--google-setup",
        action="store_true",
        help="Setup Google Gmail and Calendar integration"
    )
    
    parser.add_argument(
        "--notion-setup",
        action="store_true",
        help="Setup Notion integration"
    )
    
    parser.add_argument(
        "--telegram-setup",
        action="store_true",
        help="Setup Telegram bot"
    )
    
    args = parser.parse_args()
    
    # Version check
    if args.version:
        console.print("TESS Terminal Configurable Edition v1.0.0")
        return
    
    # Setup wizard
    if args.setup:
        success = run_setup(force=True)
        sys.exit(0 if success else 1)
    
    # Google setup wizard
    if args.google_setup:
        from tess_configurable.google_setup_wizard import run_google_setup
        success = run_google_setup()
        sys.exit(0 if success else 1)
    
    # Notion setup
    if args.notion_setup:
        console.print("\n[bold cyan]Notion Integration Setup[/bold cyan]\n")
        from tess_configurable.core.notion_client import NotionClient
        client = NotionClient()
        console.print(client.get_setup_instructions())
        sys.exit(0)
    
    # Telegram setup
    if args.telegram_setup:
        from tess_configurable.telegram_setup_wizard import run_telegram_setup
        success = run_telegram_setup()
        sys.exit(0 if success else 1)
    
    # Settings menu
    if args.settings:
        open_settings()
        return
    
    # Reset config
    if args.reset:
        if Confirm.ask("Reset all configuration?"):
            mgr = get_config_manager()
            mgr.reset_to_defaults()
            mgr.save()
            console.print("[green]Configuration reset.[/green]")
        return
    
    # Run TESS
    tess = TessTerminal()
    
    # Single command mode
    if args.command:
        tess.run_single(args.command)
        return
    
    # Interactive mode
    if tess.initialize():
        tess.run()
    else:
        console.print("[red]Failed to initialize TESS.[/red]")
        console.print("[dim]Run 'tess --setup' to configure.[/dim]")
        sys.exit(1)


if __name__ == "__main__":
    main()
