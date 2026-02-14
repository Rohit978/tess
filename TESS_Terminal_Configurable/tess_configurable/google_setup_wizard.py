"""
Google OAuth Setup Wizard
Guides users through setting up Gmail and Calendar step-by-step.
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


class GoogleSetupWizard:
    """
    Interactive wizard for Google OAuth setup.
    Guides users through creating credentials and enabling APIs.
    """
    
    def __init__(self):
        self.config = get_config_manager()
        self.credentials_path = None
        
    def run(self) -> bool:
        """
        Run the Google setup wizard.
        
        Returns:
            True if setup completed successfully
        """
        console.print(Panel.fit(
            "[bold cyan]Google Services Setup[/bold cyan]\n"
            "[dim]Gmail and Calendar Integration[/dim]\n\n"
            "This wizard will guide you through:\n"
            "1. Creating a Google Cloud project\n"
            "2. Enabling Gmail and Calendar APIs\n"
            "3. Creating OAuth credentials\n"
            "4. Connecting TESS to your Google account",
            title="📧 Gmail + 📅 Calendar",
            border_style="cyan"
        ))
        
        console.print("\n[bold]Prerequisites:[/bold]")
        console.print("• A Google account (Gmail)")
        console.print("• About 5 minutes of your time\n")
        
        if not Confirm.ask("Ready to start?"):
            return False
        
        # Step 1: Open Google Cloud Console
        if not self._step1_create_project():
            return False
        
        # Step 2: Enable APIs
        self._step2_enable_apis()
        
        # Step 3: Create OAuth credentials
        if not self._step3_create_oauth():
            return False
        
        # Step 4: Load credentials
        if not self._step4_load_credentials():
            return False
        
        # Step 5: Test connection
        self._step5_test_connection()
        
        return True
    
    def _step1_create_project(self) -> bool:
        """Guide user to create Google Cloud project."""
        console.print("\n[bold blue]Step 1: Create Google Cloud Project[/bold blue]\n")
        
        console.print("""
1. Opening [link=https://console.cloud.google.com/projectcreate]Google Cloud Console[/link]...
2. Sign in with your Google account if needed
3. Enter project name: [cyan]TESS Terminal[/cyan]
4. Click [bold]CREATE[/bold]
""")
        
        if Confirm.ask("Open Google Cloud Console in browser?", default=True):
            webbrowser.open("https://console.cloud.google.com/projectcreate")
        
        console.print("\n[dim]Waiting for you to create the project...[/dim]")
        
        while True:
            done = Confirm.ask("\nHave you created the project?", default=False)
            if done:
                break
            if not Confirm.ask("Continue waiting?", default=True):
                return False
        
        return True
    
    def _step2_enable_apis(self):
        """Guide user to enable APIs."""
        console.print("\n[bold blue]Step 2: Enable Gmail and Calendar APIs[/bold blue]\n")
        
        console.print("""
1. Make sure your [cyan]TESS Terminal[/cyan] project is selected
2. Go to [bold]APIs & Services[/bold] → [bold]Library[/bold]
3. Search for and enable:
   • [green]✓[/green] Gmail API
   • [green]✓[/green] Google Calendar API
""")
        
        if Confirm.ask("Open API Library in browser?", default=True):
            webbrowser.open("https://console.cloud.google.com/apis/library")
        
        console.print("\n[dim]Waiting for you to enable the APIs...[/dim]")
        
        while True:
            done = Confirm.ask("\nHave you enabled both APIs?", default=False)
            if done:
                break
            if not Confirm.ask("Continue waiting?", default=True):
                return
    
    def _step3_create_oauth(self) -> bool:
        """Guide user to create OAuth credentials."""
        console.print("\n[bold blue]Step 3: Create OAuth Credentials[/bold blue]\n")
        
        console.print("[bold]Part A: Configure Consent Screen[/bold]\n")
        console.print("""
1. Go to [bold]APIs & Services[/bold] → [bold]OAuth consent screen[/bold]
2. Select [cyan]External[/cyan] (for personal use) → Click [bold]CREATE[/bold]
3. Fill in:
   • App name: [cyan]TESS Terminal[/cyan]
   • User support email: [cyan]your-email@gmail.com[/cyan]
   • Developer contact: [cyan]your-email@gmail.com[/cyan]
4. Click [bold]Save and Continue[/bold] (3 times)
5. Click [bold]Back to Dashboard[/bold]
""")
        
        if Confirm.ask("Open OAuth consent screen?", default=True):
            webbrowser.open("https://console.cloud.google.com/apis/credentials/consent")
        
        while True:
            done = Confirm.ask("\nHave you configured the consent screen?", default=False)
            if done:
                break
            if not Confirm.ask("Continue waiting?", default=True):
                return False
        
        console.print("\n[bold]Part B: Create Credentials[/bold]\n")
        console.print("""
1. Go to [bold]APIs & Services[/bold] → [bold]Credentials[/bold]
2. Click [bold]+ Create Credentials[/bold] → [bold]OAuth client ID[/bold]
3. Select [cyan]Desktop app[/cyan]
4. Name: [cyan]TESS Desktop[/cyan]
5. Click [bold]CREATE[/bold]
6. Click [bold]DOWNLOAD JSON[/bold] - Save the file somewhere safe!
""")
        
        if Confirm.ask("Open Credentials page?", default=True):
            webbrowser.open("https://console.cloud.google.com/apis/credentials")
        
        while True:
            done = Confirm.ask("\nHave you downloaded the credentials JSON file?", default=False)
            if done:
                break
            if not Confirm.ask("Continue waiting?", default=True):
                return False
        
        return True
    
    def _step4_load_credentials(self) -> bool:
        """Help user place credentials file in correct location."""
        console.print("\n[bold blue]Step 4: Add Credentials to TESS[/bold blue]\n")
        
        # Show config directory
        config_dir = self.config.config_dir
        console.print(f"TESS config directory: [cyan]{config_dir}[/cyan]\n")
        
        # Ensure directory exists
        config_dir.mkdir(parents=True, exist_ok=True)
        
        # Show options
        console.print("[bold]Options:[/bold]\n")
        console.print("[1] I'll copy the file manually")
        console.print("[2] Tell me the path and I'll copy it")
        console.print("[3] Paste the credentials content directly\n")
        
        choice = Prompt.ask("Select option", choices=["1", "2", "3"], default="2")
        
        if choice == "1":
            console.print(f"\n[cyan]Please copy your credentials.json to:[/cyan]")
            console.print(f"[bold]{config_dir / 'credentials.json'}[/bold]\n")
            input("Press Enter when done...")
            
        elif choice == "2":
            source_path = Prompt.ask("Enter full path to your credentials.json file")
            source = Path(source_path.strip('"'))
            
            if not source.exists():
                console.print("[red]✗ File not found![/red]")
                return False
            
            # Copy file
            import shutil
            dest = config_dir / "credentials.json"
            shutil.copy2(source, dest)
            console.print(f"[green]✓ Copied to {dest}[/green]")
            
        elif choice == "3":
            console.print("\n[cyan]Paste the entire JSON content below:[/cyan]")
            console.print("[dim](Press Ctrl+Z then Enter when done on Windows)[/dim]")
            console.print("[dim](Press Ctrl+D when done on Mac/Linux)[/dim]\n")
            
            lines = []
            try:
                while True:
                    try:
                        line = input()
                        lines.append(line)
                    except EOFError:
                        break
            except KeyboardInterrupt:
                pass
            
            json_content = "\n".join(lines)
            
            # Validate JSON
            try:
                import json
                json.loads(json_content)
                
                dest = config_dir / "credentials.json"
                with open(dest, 'w') as f:
                    f.write(json_content)
                console.print(f"[green]✓ Saved to {dest}[/green]")
            except json.JSONDecodeError:
                console.print("[red]✗ Invalid JSON content![/red]")
                return False
        
        # Enable features in config
        self.config.config.features.gmail = True
        self.config.config.features.calendar = True
        self.config.config.google.credentials_file = str(config_dir / "credentials.json")
        self.config.save()
        
        console.print("\n[green]✓ Gmail and Calendar enabled in TESS![/green]")
        return True
    
    def _step5_test_connection(self):
        """Test the Google connection."""
        console.print("\n[bold blue]Step 5: Test Connection[/bold blue]\n")
        
        console.print("Now let's test the connection. TESS will:")
        console.print("1. Open your browser for Google sign-in")
        console.print("2. Ask for permission to access Gmail/Calendar")
        console.print("3. Save the authentication token\n")
        
        if Confirm.ask("Test now?", default=True):
            try:
                from .google_client import GoogleClient
                
                client = GoogleClient()
                
                console.print("\n[cyan]Opening browser for authentication...[/cyan]")
                console.print("[dim]Please sign in and grant permissions[/dim]\n")
                
                # Try to list emails (will trigger auth)
                result = client.list_emails(max_results=1)
                
                if "not authenticated" not in result.lower() and "error" not in result.lower():
                    console.print("[green]✓ Successfully connected to Gmail![/green]")
                else:
                    console.print(f"[yellow]⚠ {result}[/yellow]")
                    
            except Exception as e:
                console.print(f"[yellow]⚠ Test encountered an issue: {e}[/yellow]")
                console.print("[dim]You can test again later by running 'tess \"read my emails\"'[/dim]")
        
        # Final summary
        self._show_summary()
    
    def _show_summary(self):
        """Show final summary."""
        console.print("\n" + "=" * 50)
        console.print("[bold green]Setup Complete![/bold green]")
        console.print("=" * 50 + "\n")
        
        table = Table(title="Google Services Status", box=box.ROUNDED)
        table.add_column("Service", style="cyan")
        table.add_column("Status", style="green")
        
        table.add_row("Gmail", "✓ Enabled" if self.config.config.features.gmail else "✗ Disabled")
        table.add_row("Calendar", "✓ Enabled" if self.config.config.features.calendar else "✗ Disabled")
        
        console.print(table)
        
        console.print("\n[bold]Next steps:[/bold]")
        console.print('• Test: tess "read my emails"')
        console.print('• Test: tess "check my calendar"')
        console.print('• Send: tess "send email to friend@example.com about dinner"')
        console.print("\n[dim]If you encounter issues, run: tess --google-setup[/dim]\n")


def run_google_setup() -> bool:
    """Convenience function to run the wizard."""
    wizard = GoogleSetupWizard()
    return wizard.run()


if __name__ == "__main__":
    run_google_setup()
