"""
Interactive Settings Menu (TUI) for managing TESS configuration.
"""

import os
import sys
from typing import Optional

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt, Confirm
    from rich.table import Table
    from rich.layout import Layout
    from rich.live import Live
    from rich import box
except ImportError:
    print("Installing required dependencies...")
    os.system(f"{sys.executable} -m pip install rich -q")
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt, Confirm
    from rich.table import Table
    from rich.layout import Layout
    from rich.live import Live
    from rich import box

from .config_manager import get_config_manager


console = Console()


class SettingsMenu:
    """
    Interactive settings management TUI.
    """
    
    def __init__(self):
        self.config = get_config_manager()
        self.running = True
        
    def run(self):
        """Main menu loop."""
        while self.running:
            self._clear_screen()
            self._show_header()
            self._show_main_menu()
            
    def _clear_screen(self):
        """Clear terminal screen."""
        os.system('cls' if os.name == 'nt' else 'clear')
        
    def _show_header(self):
        """Display menu header."""
        console.print(Panel.fit(
            "[bold cyan]TESS Settings[/bold cyan]\n"
            f"[dim]Config: {self.config.config_file}[/dim]",
            border_style="cyan"
        ))
        
    def _show_main_menu(self):
        """Display and handle main menu."""
        menu_items = [
            ("1", "LLM Configuration", self._llm_menu),
            ("2", "Security Settings", self._security_menu),
            ("3", "Feature Toggles", self._features_menu),
            ("4", "Telegram Bot", self._telegram_menu),
            ("5", "View Current Config", self._view_config),
            ("6", "Export/Import Config", self._export_import_menu),
            ("7", "Test API Keys", self._test_keys),
            ("0", "Save & Exit", self._exit),
        ]
        
        console.print("\n[bold]Main Menu[/bold]\n")
        for num, name, _ in menu_items:
            console.print(f"  [{num}] {name}")
        
        choice = Prompt.ask(
            "\nSelect option",
            choices=[item[0] for item in menu_items],
            default="0"
        )
        
        # Find and execute handler
        for num, _, handler in menu_items:
            if num == choice:
                handler()
                break
    
    def _llm_menu(self):
        """LLM configuration submenu."""
        while True:
            self._clear_screen()
            console.print("\n[bold]LLM Configuration[/bold]\n")
            
            # Show current providers
            table = Table(title="Configured Providers", box=box.ROUNDED)
            table.add_column("Provider", style="cyan")
            table.add_column("Status", style="green")
            table.add_column("Keys", style="magenta")
            table.add_column("Model", style="yellow")
            
            for provider in ["groq", "openai", "deepseek", "gemini"]:
                keys = self.config.get_all_api_keys(provider)
                key_count = len(keys)
                
                if key_count > 0:
                    status = f"[green]✓ Configured[/green]"
                    key_status = f"[green]{key_count} key{'s' if key_count > 1 else ''}[/green]"
                else:
                    status = "[red]✗ Not set[/red]"
                    key_status = "[red]-[/red]"
                
                if provider == self.config.config.llm.provider:
                    model = self.config.config.llm.model
                    status += " [cyan](Primary)[/cyan]"
                else:
                    model = "-"
                    
                table.add_row(provider.upper(), status, key_status, model)
            
            console.print(table)
            
            console.print("\n[bold]Options:[/bold]")
            console.print("  [1] Change primary provider")
            console.print("  [2] Add API key (for rotation)")
            console.print("  [3] Replace API keys")
            console.print("  [4] Manage keys (view/remove)")
            console.print("  [5] Change model")
            console.print("  [0] Back to main menu")
            
            choice = Prompt.ask("Select", choices=["1", "2", "3", "4", "5", "0"], default="0")
            
            if choice == "0":
                break
            elif choice == "1":
                self._change_primary_provider()
            elif choice == "2":
                self._add_api_key()
            elif choice == "3":
                self._replace_api_keys()
            elif choice == "4":
                self._manage_keys()
            elif choice == "5":
                self._change_model()
    
    def _change_primary_provider(self):
        """Change the primary LLM provider."""
        providers = ["groq", "openai", "deepseek", "gemini"]
        console.print("\nAvailable providers:")
        for i, p in enumerate(providers, 1):
            marker = " [cyan](current)[/cyan]" if p == self.config.config.llm.provider else ""
            console.print(f"  [{i}] {p.upper()}{marker}")
        
        choice = int(Prompt.ask("Select", choices=["1", "2", "3", "4"])) - 1
        new_provider = providers[choice]
        
        # Check if key exists
        if not self.config.get_api_key(new_provider):
            console.print(f"[yellow]⚠ No API key configured for {new_provider}[/yellow]")
            if Confirm.ask("Add key now?"):
                self._prompt_for_key(new_provider)
        
        self.config.config.llm.provider = new_provider
        console.print(f"[green]✓ Primary provider changed to {new_provider.upper()}[/green]")
        input("\nPress Enter to continue...")
    
    def _add_api_key(self):
        """Add an additional API key for rotation."""
        provider = Prompt.ask(
            "Which provider?",
            choices=["groq", "openai", "deepseek", "gemini"]
        )
        
        # Check if already has keys
        existing = self.config.get_all_api_keys(provider)
        if existing:
            console.print(f"[dim]{provider} has {len(existing)} key(s) already. Adding another for rotation.[/dim]")
        
        self._prompt_for_key(provider, add_mode=True)
    
    def _replace_api_keys(self):
        """Replace all API keys for a provider."""
        provider = Prompt.ask(
            "Which provider?",
            choices=["groq", "openai", "deepseek", "gemini"]
        )
        
        # Show existing keys
        existing = self.config.get_all_api_keys(provider)
        if existing:
            console.print(f"[yellow]⚠ This will replace {len(existing)} existing key(s)[/yellow]")
            if not Confirm.ask("Continue?"):
                return
        
        self._prompt_for_key(provider, add_mode=False)
    
    def _manage_keys(self):
        """View and remove individual API keys."""
        provider = Prompt.ask(
            "Which provider?",
            choices=["groq", "openai", "deepseek", "gemini"]
        )
        
        keys = self.config.get_all_api_keys(provider)
        
        if not keys:
            console.print(f"[yellow]No keys configured for {provider}[/yellow]")
            input("\nPress Enter to continue...")
            return
        
        while True:
            self._clear_screen()
            console.print(f"\n[bold]{provider.upper()} Keys[/bold]\n")
            
            table = Table(box=box.ROUNDED)
            table.add_column("#", style="cyan")
            table.add_column("Key Preview", style="green")
            table.add_column("Status", style="yellow")
            
            for i, key in enumerate(keys, 1):
                # Mask key for display
                masked = key[:6] + "..." + key[-4:] if len(key) > 12 else "****"
                status = "[green]Active[/green]" if i == 1 else "[dim]Rotation[/dim]"
                table.add_row(str(i), masked, status)
            
            console.print(table)
            console.print("\n[bold]Options:[/bold]")
            console.print("  [1] Remove a key")
            console.print("  [2] Test all keys")
            console.print("  [0] Back")
            
            choice = Prompt.ask("Select", choices=["1", "2", "0"], default="0")
            
            if choice == "0":
                break
            elif choice == "1":
                if len(keys) == 1:
                    if Confirm.ask(f"Remove the only key for {provider}?", default=False):
                        self.config.config.llm.api_keys[provider] = []
                        console.print(f"[green]✓ Key removed[/green]")
                        break
                else:
                    idx = int(Prompt.ask("Remove key #", choices=[str(i) for i in range(1, len(keys)+1)])) - 1
                    if self.config.remove_api_key(provider, idx):
                        keys = self.config.get_all_api_keys(provider)
                        console.print(f"[green]✓ Key removed[/green]")
            elif choice == "2":
                self._test_provider_keys(provider)
    
    def _test_provider_keys(self, provider: str):
        """Test all keys for a provider."""
        console.print(f"\n[dim]Testing {provider} keys...[/dim]")
        keys = self.config.get_all_api_keys(provider)
        
        for i, key in enumerate(keys, 1):
            # Simple validation check
            is_valid, msg = self.config.validate_api_key(provider, key)
            if is_valid:
                console.print(f"  Key {i}: [green]✓ Valid format[/green]")
            else:
                console.print(f"  Key {i}: [red]✗ {msg}[/red]")
        
        input("\nPress Enter to continue...")
    
    def _prompt_for_key(self, provider: str, add_mode: bool = False):
        """Prompt for and validate an API key."""
        console.print(f"\n[dim]Get your key from:[/dim] {self._get_key_url(provider)}")
        console.print("[dim]Type or paste your key (input is visible for easier editing)[/dim]")
        
        key = input(f"Enter {provider} API key: ")
        
        # Show feedback
        if key:
            masked = key[:4] + "****" + key[-4:] if len(key) > 8 else "****"
            console.print(f"[dim]Received: {masked}[/dim]")
        
        if key:
            is_valid, msg = self.config.validate_api_key(provider, key)
            if is_valid:
                if add_mode:
                    if self.config.add_api_key(provider, key):
                        console.print(f"[green]✓ {provider} key added for rotation[/green]")
                    else:
                        console.print(f"[yellow]⚠ Key already exists[/yellow]")
                else:
                    self.config.set_api_key(provider, key)
                    console.print(f"[green]✓ {provider} key updated[/green]")
            else:
                console.print(f"[yellow]⚠ {msg}[/yellow]")
                if Confirm.ask("Save anyway?"):
                    if add_mode:
                        if self.config.add_api_key(provider, key):
                            console.print(f"[green]✓ {provider} key saved[/green]")
                    else:
                        self.config.set_api_key(provider, key)
                        console.print(f"[green]✓ {provider} key saved[/green]")
        
        input("\nPress Enter to continue...")
    
    def _change_model(self):
        """Change the model for current provider."""
        provider = self.config.config.llm.provider
        models = self._get_models_for_provider(provider)
        
        console.print(f"\n[bold]Available models for {provider}:[/bold]")
        for i, model in enumerate(models, 1):
            marker = " [cyan](current)[/cyan]" if model == self.config.config.llm.model else ""
            console.print(f"  [{i}] {model}{marker}")
        
        choice = int(Prompt.ask("Select", choices=[str(i) for i in range(1, len(models)+1)])) - 1
        self.config.config.llm.model = models[choice]
        console.print(f"[green]✓ Model updated[/green]")
        input("\nPress Enter to continue...")
    
    def _security_menu(self):
        """Security settings submenu."""
        while True:
            self._clear_screen()
            console.print("\n[bold]Security Settings[/bold]\n")
            
            table = Table(box=box.ROUNDED)
            table.add_column("Setting", style="cyan")
            table.add_column("Current Value", style="green")
            
            table.add_row("Security Level", self.config.config.security.level)
            table.add_row("Safe Mode", "Enabled" if self.config.config.security.safe_mode else "Disabled")
            table.add_row("Confirm Dangerous", "Enabled" if self.config.config.security.confirm_dangerous else "Disabled")
            
            console.print(table)
            
            console.print("\n[bold]Options:[/bold]")
            console.print("  [1] Change security level")
            console.print("  [2] Toggle safe mode")
            console.print("  [3] Toggle confirm dangerous")
            console.print("  [4] View blocked commands")
            console.print("  [0] Back")
            
            choice = Prompt.ask("Select", choices=["1", "2", "3", "4", "0"], default="0")
            
            if choice == "0":
                break
            elif choice == "1":
                level = Prompt.ask("Security level", choices=["LOW", "MEDIUM", "HIGH"],
                                  default=self.config.config.security.level)
                self.config.config.security.level = level
            elif choice == "2":
                self.config.config.security.safe_mode = not self.config.config.security.safe_mode
            elif choice == "3":
                self.config.config.security.confirm_dangerous = not self.config.config.security.confirm_dangerous
            elif choice == "4":
                console.print("\n[dim]Blocked Commands:[/dim]")
                for cmd in self.config.config.security.blocked_commands:
                    console.print(f"  • {cmd}")
                input("\nPress Enter to continue...")
    
    def _features_menu(self):
        """Feature toggles submenu."""
        while True:
            self._clear_screen()
            console.print("\n[bold]Feature Toggles[/bold]\n")
            
            table = Table(box=box.ROUNDED)
            table.add_column("Feature", style="cyan")
            table.add_column("Status", style="green")
            
            features = self.config.config.features
            table.add_row("Voice Input", "✓ Enabled" if features.voice_input else "✗ Disabled")
            table.add_row("Web Search", "✓ Enabled" if features.web_search else "✗ Disabled")
            table.add_row("Telegram Bot", "✓ Enabled" if features.telegram_bot else "✗ Disabled")
            
            console.print(table)
            
            console.print("\n[bold]Toggle:[/bold]")
            console.print("  [1] Voice Input")
            console.print("  [2] Web Search")
            console.print("  [3] Telegram Bot")
            console.print("  [0] Back")
            
            choice = Prompt.ask("Select", choices=["1", "2", "3", "0"], default="0")
            
            if choice == "0":
                break
            elif choice == "1":
                features.voice_input = not features.voice_input
            elif choice == "2":
                features.web_search = not features.web_search
            elif choice == "3":
                features.telegram_bot = not features.telegram_bot
    
    def _telegram_menu(self):
        """Telegram bot configuration."""
        self._clear_screen()
        console.print("\n[bold]Telegram Bot Configuration[/bold]\n")
        
        has_token = bool(self.config.config.telegram.bot_token)
        console.print(f"Status: {'[green]Configured[/green]' if has_token else '[red]Not configured[/red]'}\n")
        
        if Confirm.ask("Update Telegram settings?"):
            console.print("[dim]Get token from @BotFather on Telegram[/dim]")
            console.print("[dim]Type or paste your token (input is hidden)[/dim]")
            
            token = input("Bot Token (press Enter to keep current): ")
            if token:
                masked = token[:6] + "****" if len(token) > 6 else "****"
                console.print(f"[dim]Token received: {masked}[/dim]")
            
            if token:
                self.config.config.telegram.bot_token = token
            
            user_id = Prompt.ask("Your Telegram User ID", default=self.config.config.telegram.user_id)
            self.config.config.telegram.user_id = user_id
            
            console.print("[green]✓ Telegram settings updated[/green]")
            input("\nPress Enter to continue...")
    
    def _view_config(self):
        """Display full current configuration."""
        self._clear_screen()
        console.print("\n[bold]Current Configuration[/bold]\n")
        
        import json
        from dataclasses import asdict
        
        config_dict = {
            'llm': asdict(self.config.config.llm),
            'security': asdict(self.config.config.security),
            'features': asdict(self.config.config.features),
            'paths': asdict(self.config.config.paths),
            'telegram': asdict(self.config.config.telegram),
            'version': self.config.config.version
        }
        
        # Mask API keys for display
        for provider in config_dict['llm']['api_keys']:
            key = config_dict['llm']['api_keys'][provider]
            if key:
                config_dict['llm']['api_keys'][provider] = key[:8] + "****" + key[-4:]
        
        console.print_json(json.dumps(config_dict, indent=2))
        input("\nPress Enter to continue...")
    
    def _export_import_menu(self):
        """Export/import configuration."""
        self._clear_screen()
        console.print("\n[bold]Export/Import Configuration[/bold]\n")
        
        console.print("  [1] Export config to file")
        console.print("  [2] Import config from file")
        console.print("  [0] Back")
        
        choice = Prompt.ask("Select", choices=["1", "2", "0"], default="0")
        
        if choice == "1":
            path = Prompt.ask("Export path", default="tess_config_backup.json")
            if self.config.export_config(path):
                console.print(f"[green]✓ Config exported to {path}[/green]")
            else:
                console.print("[red]✗ Export failed[/red]")
        elif choice == "2":
            path = Prompt.ask("Import file path")
            if os.path.exists(path):
                if self.config.import_config(path):
                    console.print(f"[green]✓ Config imported from {path}[/green]")
                else:
                    console.print("[red]✗ Import failed[/red]")
            else:
                console.print("[red]✗ File not found[/red]")
        
        input("\nPress Enter to continue...")
    
    def _test_keys(self):
        """Test configured API keys."""
        self._clear_screen()
        console.print("\n[bold]Testing API Keys[/bold]\n")
        
        for provider in ["groq", "openai", "deepseek", "gemini"]:
            key = self.config.get_api_key(provider)
            if key:
                # TODO: Add actual API test calls
                is_valid, msg = self.config.validate_api_key(provider, key)
                status = "[green]✓ Valid[/green]" if is_valid else f"[red]✗ {msg}[/red]"
                console.print(f"{provider.upper()}: {status}")
            else:
                console.print(f"{provider.upper()}: [dim]Not configured[/dim]")
        
        input("\nPress Enter to continue...")
    
    def _exit(self):
        """Save and exit."""
        if self.config.save():
            console.print("\n[green]✓ Configuration saved[/green]")
        else:
            console.print("\n[red]✗ Failed to save configuration[/red]")
        self.running = False
    
    def _get_key_url(self, provider: str) -> str:
        """Get URL for API key generation."""
        urls = {
            "groq": "https://console.groq.com/keys",
            "openai": "https://platform.openai.com/api-keys",
            "deepseek": "https://platform.deepseek.com/api_keys",
            "gemini": "https://aistudio.google.com/app/apikey"
        }
        return urls.get(provider, "Provider website")
    
    def _get_models_for_provider(self, provider: str) -> list:
        """Get available models for a provider."""
        models = {
            "groq": ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768", "gemma2-9b-it"],
            "openai": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
            "deepseek": ["deepseek-chat", "deepseek-coder"],
            "gemini": ["gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"]
        }
        return models.get(provider, [])


def open_settings():
    """Convenience function to open settings menu."""
    menu = SettingsMenu()
    menu.run()


if __name__ == "__main__":
    open_settings()
