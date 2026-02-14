"""
Interactive Setup Wizard for first-time configuration.
Full feature version.
"""

import os
import sys
from typing import Optional

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt, Confirm
    from rich.table import Table
    from rich import box
except ImportError:
    print("Installing required dependencies...")
    os.system(f"{sys.executable} -m pip install rich -q")
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt, Confirm
    from rich.table import Table
    from rich import box

from .config_manager import get_config_manager, LLMConfig, SecurityConfig, FeatureConfig


console = Console()


class SetupWizard:
    """
    Interactive wizard for first-time TESS setup.
    Configures all features including optional ones.
    """
    
    def __init__(self):
        self.config = get_config_manager()
        
    def run(self, force: bool = False) -> bool:
        """
        Run the setup wizard.
        
        Args:
            force: Run even if already configured
            
        Returns:
            True if setup completed successfully
        """
        if not force and not self.config.config.first_run and self.config.is_configured():
            console.print("[green]✓ TESS is already configured![/green]")
            console.print(f"Config location: {self.config.config_file}")
            if not Confirm.ask("Would you like to reconfigure?"):
                return True
        
        console.print(Panel.fit(
            "[bold cyan]Welcome to TESS Terminal[/bold cyan]\n"
            "[dim]The Configurable AI Agent[/dim]\n\n"
            "Let's get you set up! This wizard will guide you through\n"
            "configuring your LLM providers and all available features.",
            title="🤖 TESS Setup",
            border_style="cyan"
        ))
        
        # Step 1: LLM Provider Selection
        if not self._setup_llm():
            return False
            
        # Step 2: Security Settings
        self._setup_security()
        
        # Step 3: Core Features
        self._setup_core_features()
        
        # Step 4: Communication Features
        self._setup_communication()
        
        # Step 5: Media & Web
        self._setup_media_web()
        
        # Step 6: Advanced AI Features
        self._setup_ai_features()
        
        # Step 7: Optional Integrations
        self._setup_integrations()
        
        # Finalize
        self.config.config.first_run = False
        if self.config.save():
            console.print("\n[green]✓ Configuration saved successfully![/green]")
            console.print(f"[dim]Config file: {self.config.config_file}[/dim]\n")
            self._show_summary()
            return True
        else:
            console.print("\n[red]✗ Failed to save configuration[/red]")
            return False
    
    def _setup_llm(self) -> bool:
        """Configure LLM providers and API keys."""
        console.print("\n[bold]Step 1: LLM Configuration[/bold]")
        console.print("[dim]TESS supports multiple LLM providers for redundancy.[/dim]\n")
        
        providers = ["groq", "openai", "deepseek", "gemini"]
        
        table = Table(title="Available Providers", box=box.ROUNDED)
        table.add_column("#", style="cyan")
        table.add_column("Provider", style="green")
        table.add_column("Description", style="dim")
        
        table.add_row("1", "Groq", "Fast, free tier available (Recommended)")
        table.add_row("2", "OpenAI", "GPT-4, reliable but paid")
        table.add_row("3", "DeepSeek", "Good for coding tasks")
        table.add_row("4", "Gemini", "Google's models, generous free tier")
        
        console.print(table)
        
        choice = Prompt.ask(
            "\nSelect your primary provider",
            choices=["1", "2", "3", "4"],
            default="1"
        )
        
        provider_map = {"1": "groq", "2": "openai", "3": "deepseek", "4": "gemini"}
        primary = provider_map[choice]
        self.config.config.llm.provider = primary
        
        console.print(f"\n[blue]Primary provider set to: {primary.upper()}[/blue]")
        
        keys_configured = 0
        for provider in providers:
            console.print(f"\n[bold]{provider.upper()} API Key[/bold]")
            console.print(f"[dim]Get your key from:[/dim] {self._get_key_url(provider)}")
            
            default_yes = (provider == primary)
            if Confirm.ask(f"Configure {provider} now?", default=default_yes):
                key_num = 1
                while True:
                    key_prompt = f"Enter {provider} API key #{key_num}" if key_num > 1 else f"Enter {provider} API key"
                    key = self._visible_input(key_prompt)
                    
                    if key:
                        is_valid, msg = self.config.validate_api_key(provider, key)
                        if is_valid:
                            if key_num == 1:
                                self.config.set_api_key(provider, key)
                            else:
                                self.config.add_api_key(provider, key)
                            keys_configured += 1
                            console.print(f"[green]✓ {provider} key #{key_num} configured[/green]")
                        else:
                            console.print(f"[yellow]⚠ {msg}[/yellow]")
                            if Confirm.ask("Save anyway?"):
                                if key_num == 1:
                                    self.config.set_api_key(provider, key)
                                else:
                                    self.config.add_api_key(provider, key)
                                keys_configured += 1
                        
                        # Ask if user wants to add another key for this provider
                        if Confirm.ask(f"Add another {provider} key for rotation?", default=False):
                            key_num += 1
                            continue
                    break
        
        if keys_configured == 0:
            console.print("\n[red]✗ No API keys configured. TESS requires at least one.[/red]")
            return False
        
        # Model selection
        models = self._get_models_for_provider(primary)
        if models:
            console.print(f"\n[bold]Select model for {primary}:[/bold]")
            for i, model in enumerate(models, 1):
                console.print(f"  {i}. {model}")
            
            model_choice = Prompt.ask("Model", choices=[str(i) for i in range(1, len(models)+1)], default="1")
            self.config.config.llm.model = models[int(model_choice)-1]
        
        return True
    
    def _setup_security(self):
        """Configure security settings."""
        console.print("\n[bold]Step 2: Security Settings[/bold]")
        
        levels = {
            "LOW": "Minimal protection, faster workflow",
            "MEDIUM": "Balanced security (Recommended)",
            "HIGH": "Maximum protection, all actions confirmed"
        }
        
        console.print("\nSecurity Levels:")
        for level, desc in levels.items():
            console.print(f"  • {level}: {desc}")
        
        level = Prompt.ask(
            "Select security level",
            choices=["LOW", "MEDIUM", "HIGH"],
            default="MEDIUM"
        )
        self.config.config.security.level = level
        
        self.config.config.security.safe_mode = Confirm.ask(
            "Enable safe mode? (asks before executing commands)",
            default=True
        )
    
    def _setup_core_features(self):
        """Configure core features."""
        console.print("\n[bold]Step 3: Core Features[/bold]")
        
        f = self.config.config.features
        
        f.web_search = Confirm.ask(
            "Enable web search?",
            default=True
        )
        
        f.memory = Confirm.ask(
            "Enable memory? (stores conversation history)",
            default=True
        )
        
        f.planner = Confirm.ask(
            "Enable planner? (breaks down complex tasks)",
            default=True
        )
        
        f.skills = Confirm.ask(
            "Enable skills? (learn reusable task patterns)",
            default=True
        )
    
    def _setup_communication(self):
        """Configure communication features."""
        console.print("\n[bold]Step 4: Communication Features[/bold]")
        console.print("[dim]Optional: WhatsApp, Gmail, Calendar integration[/dim]\n")
        
        f = self.config.config.features
        
        if Confirm.ask("Enable WhatsApp? (requires QR scan on first use)", default=False):
            f.whatsapp = True
            console.print("[yellow]⚠ You'll need to scan QR code when first using WhatsApp[/yellow]")
        
        if Confirm.ask("Enable Gmail? (requires Google OAuth)", default=False):
            f.gmail = True
        
        if Confirm.ask("Enable Calendar? (requires Google OAuth)", default=False):
            f.calendar = True
    
    def _setup_media_web(self):
        """Configure media and web features."""
        console.print("\n[bold]Step 5: Media & Web[/bold]")
        
        f = self.config.config.features
        
        f.youtube = Confirm.ask(
            "Enable YouTube control? (play/pause videos)",
            default=False
        )
        
        f.web_scraping = Confirm.ask(
            "Enable web scraping? (extract content from websites)",
            default=False
        )
    
    def _setup_ai_features(self):
        """Configure advanced AI features."""
        console.print("\n[bold]Step 6: Advanced AI Features[/bold]")
        
        f = self.config.config.features
        
        f.research = Confirm.ask(
            "Enable deep research? (multi-step research reports)",
            default=True
        )
        
        f.trip_planner = Confirm.ask(
            "Enable trip planner? (travel itinerary generation)",
            default=True
        )
        
        f.code_generation = Confirm.ask(
            "Enable code generation? (write & execute scripts)",
            default=True
        )
        
        f.file_converter = Confirm.ask(
            "Enable file converter? (images to PDF, etc.)",
            default=True
        )
        
        f.organizer = Confirm.ask(
            "Enable file organizer? (auto-organize folders)",
            default=True
        )
    
    def _setup_integrations(self):
        """Configure optional integrations."""
        console.print("\n[bold]Step 7: Optional Integrations[/bold]")
        
        f = self.config.config.features
        
        # Telegram
        if Confirm.ask("Configure Telegram Bot?", default=False):
            console.print("[dim]Get bot token from @BotFather on Telegram[/dim]")
            console.print("[dim]Type or paste your token (input is hidden)[/dim]")
            
            console.print("[dim]Your token will be visible while typing (for easier editing)[/dim]")
            token = input("Bot Token: ")
            if token:
                masked = token[:6] + "****" if len(token) > 6 else "****"
                console.print(f"[dim]Token received: {masked}[/dim]")
            
            user_id = Prompt.ask("Your Telegram User ID")
            
            self.config.config.telegram.bot_token = token
            self.config.config.telegram.user_id = user_id
            f.telegram_bot = True
        
        # Librarian (file watcher)
        if Confirm.ask("Enable Librarian? (auto-learn from file changes - uses more resources)", default=False):
            f.librarian = True
        
        # Web Interface
        if Confirm.ask("Enable Web Interface? (access TESS via browser)", default=False):
            f.web_interface = True
            port = Prompt.ask("Web port", default="8000")
            f.web_port = int(port)
    
    def _visible_input(self, prompt: str) -> str:
        """Get visible input for easier editing and pasting."""
        console.print(f"\n[cyan]{prompt}[/cyan]")
        console.print("[dim]Type or paste your key (input is visible for easier editing)[/dim]")
        key = input("Key: ")
        
        # Show feedback that something was entered
        if key:
            masked = key[:4] + "****" + key[-4:] if len(key) > 8 else "****"
            console.print(f"[green]✓ Received: {masked}[/green]")
        
        return key
    
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
    
    def _show_summary(self):
        """Display configuration summary."""
        table = Table(title="Configuration Summary", box=box.ROUNDED)
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="green")
        
        f = self.config.config.features
        
        table.add_row("Primary Provider", self.config.config.llm.provider.upper())
        table.add_row("Model", self.config.config.llm.model)
        table.add_row("API Keys", str(len(self.config.config.llm.api_keys)))
        table.add_row("Security Level", self.config.config.security.level)
        table.add_row("Safe Mode", "✓" if self.config.config.security.safe_mode else "✗")
        
        console.print(table)
        
        # Feature summary
        feature_table = Table(title="Enabled Features", box=box.ROUNDED)
        feature_table.add_column("Category", style="cyan")
        feature_table.add_column("Features", style="green")
        
        core = []
        if f.web_search: core.append("Web Search")
        if f.memory: core.append("Memory")
        if f.planner: core.append("Planner")
        if f.skills: core.append("Skills")
        feature_table.add_row("Core", ", ".join(core) if core else "None")
        
        comm = []
        if f.whatsapp: comm.append("WhatsApp")
        if f.gmail: comm.append("Gmail")
        if f.calendar: comm.append("Calendar")
        if f.telegram_bot: comm.append("Telegram")
        feature_table.add_row("Communication", ", ".join(comm) if comm else "None")
        
        media = []
        if f.youtube: media.append("YouTube")
        if f.web_scraping: media.append("Web Scraping")
        feature_table.add_row("Media/Web", ", ".join(media) if media else "None")
        
        ai = []
        if f.research: ai.append("Research")
        if f.trip_planner: ai.append("Trip Planner")
        if f.code_generation: ai.append("Code Gen")
        if f.file_converter: ai.append("Converter")
        if f.organizer: ai.append("Organizer")
        feature_table.add_row("AI Features", ", ".join(ai) if ai else "None")
        
        console.print(feature_table)
        console.print("\n[dim]Run 'tess --settings' anytime to change these.[/dim]")


def run_setup(force: bool = False) -> bool:
    """Convenience function to run the wizard."""
    wizard = SetupWizard()
    return wizard.run(force)


if __name__ == "__main__":
    run_setup(force=True)
