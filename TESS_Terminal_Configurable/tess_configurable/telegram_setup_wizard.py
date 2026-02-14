"""
Telegram Bot Setup Wizard
Guides users through creating and configuring a Telegram bot for TESS.
"""

import os
import webbrowser
from pathlib import Path
from typing import Optional

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt, Confirm
    from rich.table import Table
    from rich import box
except ImportError:
    print("Installing rich...")
    import subprocess
    subprocess.run(["pip", "install", "rich", "-q"], check=True)
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt, Confirm
    from rich.table import Table
    from rich import box

from .config_manager import get_config_manager


console = Console()


class TelegramSetupWizard:
    """
    Interactive wizard for Telegram Bot setup.
    Guides users through:
    1. Creating a bot with BotFather
    2. Getting the API token
    3. Finding their User ID
    4. Configuring TESS
    5. Testing the connection
    """
    
    def __init__(self):
        self.config = get_config_manager()
        self.bot_token = None
        self.user_id = None
        
    def run(self) -> bool:
        """
        Run the Telegram setup wizard.
        
        Returns:
            True if setup completed successfully
        """
        console.print(Panel.fit(
            "[bold cyan]Telegram Bot Setup[/bold cyan]\n"
            "[dim]Control TESS remotely via Telegram[/dim]\n\n"
            "This wizard will guide you through:\n"
            "1. Creating a Telegram bot with @BotFather\n"
            "2. Getting your API token\n"
            "3. Finding your Telegram User ID\n"
            "4. Connecting TESS to Telegram\n"
            "5. Testing the bot",
            title="🤖 Telegram Integration",
            border_style="cyan"
        ))
        
        console.print("\n[bold]What you need:[/bold]")
        console.print("• Telegram app installed on your phone or computer")
        console.print("• About 5 minutes of your time\n")
        
        if not Confirm.ask("Ready to start?"):
            return False
        
        # Step 1: Create bot with BotFather
        if not self._step1_create_bot():
            return False
        
        # Step 2: Get User ID
        if not self._step2_get_user_id():
            return False
        
        # Step 3: Configure TESS
        if not self._step3_configure_tess():
            return False
        
        # Step 4: Test connection
        self._step4_test_connection()
        
        return True
    
    def _step1_create_bot(self) -> bool:
        """Guide user to create bot with BotFather."""
        console.print("\n[bold blue]Step 1: Create Telegram Bot[/bold blue]\n")
        
        console.print("""
1. Open Telegram app
2. Search for [@BotFather](https://t.me/botfather) (official bot creator)
3. Click [bold]START[/bold] or send /start
4. Send command: [cyan]/newbot[/cyan]
5. Follow prompts:
   • Enter bot name (e.g., "My TESS Bot")
   • Enter username (must end in 'bot', e.g., "mytess_bot")
6. BotFather will give you a token like:
   [green]123456789:ABCdefGHIjklMNOpqrSTUvwxyz[/green]
   [bold]Copy this token![/bold]
""")
        
        if Confirm.ask("Open Telegram Web in browser?", default=True):
            webbrowser.open("https://web.telegram.org/k/#@BotFather")
        
        console.print("\n[dim]Waiting for you to create the bot...[/dim]")
        
        while True:
            done = Confirm.ask("\nHave you received the API token from BotFather?", default=False)
            if done:
                break
            if not Confirm.ask("Continue waiting?", default=True):
                return False
        
        # Get token from user
        console.print("\n[cyan]Paste your API token below:[/cyan]")
        console.print("[dim]Tip: The token looks like: 123456789:ABCdefGHIjklMNOpqrSTUvwxyz[/dim]")
        console.print("[dim]Input is visible for easier editing and pasting[/dim]")
        
        token = input("\nBot Token: ")
        
        # Validate token format
        if not token or ":" not in token:
            console.print("[red]✗ Invalid token format![/red]")
            console.print("[dim]Token should contain a colon (e.g., 123456789:ABC...)[/dim]")
            return False
        
        # Show masked token
        parts = token.split(":")
        if len(parts) == 2:
            masked = f"{parts[0][:3]}***:{parts[1][:6]}***"
            console.print(f"[green]✓ Token received: {masked}[/green]")
        
        self.bot_token = token
        return True
    
    def _step2_get_user_id(self) -> bool:
        """Guide user to get their Telegram User ID."""
        console.print("\n[bold blue]Step 2: Get Your Telegram User ID[/bold blue]\n")
        
        console.print("""
TESS needs your User ID for security (so only YOU can control it).

Option 1: Using @userinfobot (Easiest)
1. Search for [@userinfobot](https://t.me/userinfobot) in Telegram
2. Click [bold]START[/bold]
3. Bot will reply with your ID (e.g., [green]123456789[/green])

Option 2: Using @BotFather
1. Message @BotFather: [cyan]/mybots[/cyan]
2. Click your bot name
3. Click 'Bot Settings' → 'Allow Groups' → 'Disable'
   (For security - prevents others adding your bot to groups)
""")
        
        if Confirm.ask("Open @userinfobot in browser?", default=True):
            webbrowser.open("https://web.telegram.org/k/#@userinfobot")
        
        console.print("\n[dim]Waiting for you to get your User ID...[/dim]")
        
        while True:
            done = Confirm.ask("\nDo you have your User ID?", default=False)
            if done:
                break
            if not Confirm.ask("Continue waiting?", default=True):
                return False
        
        # Get User ID
        user_id = Prompt.ask("Enter your Telegram User ID")
        
        # Validate (should be numbers only)
        if not user_id.isdigit():
            console.print("[yellow]⚠ Warning: User ID should be numbers only[/yellow]")
            if not Confirm.ask("Continue anyway?"):
                return False
        
        console.print(f"[green]✓ User ID: {user_id}[/green]")
        self.user_id = user_id
        return True
    
    def _step3_configure_tess(self) -> bool:
        """Save configuration to TESS."""
        console.print("\n[bold blue]Step 3: Configure TESS[/bold blue]\n")
        
        # Enable features
        self.config.config.features.telegram_bot = True
        self.config.config.telegram.bot_token = self.bot_token
        self.config.config.telegram.user_id = self.user_id
        
        # Allow this user
        if self.user_id not in self.config.config.telegram.allowed_users:
            self.config.config.telegram.allowed_users.append(self.user_id)
        
        # Save
        if self.config.save():
            console.print("[green]✓ Telegram configuration saved![/green]")
            console.print(f"[dim]Config file: {self.config.config_file}[/dim]")
            return True
        else:
            console.print("[red]✗ Failed to save configuration[/red]")
            return False
    
    def _step4_test_connection(self):
        """Test the Telegram bot connection."""
        console.print("\n[bold blue]Step 4: Test Connection[/bold blue]\n")
        
        console.print("Let's test if your bot is working correctly.")
        console.print("""
1. Open your bot in Telegram (search for your bot's username)
2. Click [bold]START[/bold] or send /start
3. You should see a welcome message
""")
        
        # Try to validate token by checking format
        if self.bot_token and ":" in self.bot_token:
            parts = self.bot_token.split(":")
            if len(parts) == 2 and parts[0].isdigit():
                console.print("[green]✓ Token format looks valid[/green]")
            else:
                console.print("[yellow]⚠ Token format looks unusual[/yellow]")
        
        if Confirm.ask("Open your bot in Telegram Web?", default=True):
            # Try to construct bot URL from token (bot ID is before the colon)
            try:
                bot_id = self.bot_token.split(":")[0]
                # Note: We can't directly open the bot, but we can open Telegram
                webbrowser.open(f"https://web.telegram.org/")
            except:
                webbrowser.open("https://web.telegram.org/")
        
        # Show summary
        self._show_summary()
    
    def _show_summary(self):
        """Show final summary."""
        console.print("\n" + "=" * 50)
        console.print("[bold green]Setup Complete![/bold green]")
        console.print("=" * 50 + "\n")
        
        table = Table(title="Telegram Bot Status", box=box.ROUNDED)
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="green")
        
        # Mask token for display
        if self.bot_token:
            parts = self.bot_token.split(":")
            masked = f"{parts[0][:5]}***:{parts[1][:6]}***" if len(parts) == 2 else "***"
            table.add_row("Bot Token", masked)
        
        table.add_row("User ID", self.user_id or "Not set")
        table.add_row("Status", "✓ Enabled" if self.config.config.features.telegram_bot else "✗ Disabled")
        
        console.print(table)
        
        console.print("\n[bold]Next steps:[/bold]")
        console.print("1. Send a message to your bot on Telegram")
        console.print("2. Try these commands from Telegram:")
        console.print('   /start - Start the bot')
        console.print('   /help - Show available commands')
        console.print('   "open chrome" - Execute commands remotely')
        console.print("3. To start TESS with Telegram:")
        console.print('   tess (will start both CLI and Telegram bot)')
        console.print("\n[dim]If your bot doesn't respond, check:")
        console.print("- Is the token correct?")
        console.print("- Did you send /start to your bot?")
        console.print("- Is your User ID correct?[/dim]\n")


def run_telegram_setup() -> bool:
    """Convenience function to run the wizard."""
    wizard = TelegramSetupWizard()
    return wizard.run()


if __name__ == "__main__":
    run_telegram_setup()
