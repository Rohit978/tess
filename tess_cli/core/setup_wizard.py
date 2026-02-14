import os
import json
import shutil
from .config import Config

class SetupWizard:
    """
    Advanced TESS Configuration Wizard (v5.0)
    Configures API keys, Security, Modules, and Integrations.
    Saves to ~/.tess/config.json
    """

    def __init__(self):
        self.config = Config._data.copy()
        self.config["llm"]["keys"] = {
            "groq": [],
            "openai": [],
            "deepseek": [],
            "gemini": []
        }

    def run(self):
        print("\n🧙‍♂️  TESS TERMINAL PRO - SETUP WIZARD (v5.0)")
        print("==========================================")
        print("Prepare your API keys. Let's configure your AI Agent.\n")

        self._setup_llm()
        self._setup_security()
        self._setup_core_features()
        self._setup_communication()
        self._setup_media_web()
        self._setup_ai_features()
        self._setup_integrations()

        self._save_config()
        print("\n✅ Setup Complete! Run 'tess' to start.")

    def _input(self, prompt, default=None):
        """Helper for input with default."""
        d_str = f" [{default}]" if default is not None else ""
        val = input(f"{prompt}{d_str}: ").strip()
        return val if val else default

    def _bool_input(self, prompt, default=True):
        """Helper for Yes/No input."""
        d_char = "Y/n" if default else "y/N"
        val = input(f"{prompt} ({d_char}): ").strip().lower()
        if not val: return default
        return val in ["y", "yes", "true", "1"]

    def _setup_llm(self):
        print("\n🔹 Step 1: Intelligence Engine (LLM)")
        
        # Provider
        print("Select Primary Provider:")
        print("  [1] Groq (Recommended - Fast & Free Tier)")
        print("  [2] OpenAI (GPT-4 - Paid)")
        print("  [3] DeepSeek (Great for Coding)")
        print("  [4] Gemini (Google)")
        
        choice = self._input("Choice", "1")
        providers = {"1": "groq", "2": "openai", "3": "deepseek", "4": "gemini"}
        provider = providers.get(choice, "groq")
        self.config["llm"]["provider"] = provider
        
        # Keys
        print(f"\nEnter API Keys for {provider.upper()}.")
        print("You can enter multiple keys separated by commas (key1,key2) to avoid rate limits.")
        keys_str = self._input(f"{provider.title()} API Keys")
        if keys_str:
            keys = [k.strip() for k in keys_str.split(",") if k.strip()]
            self.config["llm"]["keys"][provider] = keys
        
        # Optional: Add keys for others?
        if self._bool_input(f"Add backup keys for other providers?", False):
            for p in ["groq", "openai", "deepseek", "gemini"]:
                if p == provider: continue
                k_str = self._input(f"{p.title()} API Keys (Optional)", "")
                if k_str:
                    self.config["llm"]["keys"][p] = [k.strip() for k in k_str.split(",") if k.strip()]

        # Model
        default_model = "llama-3.3-70b-versatile"
        if provider == "openai": default_model = "gpt-4-turbo"
        elif provider == "gemini": default_model = "gemini-1.5-pro"
        elif provider == "deepseek": default_model = "deepseek-coder"
        
        self.config["llm"]["model"] = self._input("Primary Model Name", default_model)

    def _setup_security(self):
        print("\n🔹 Step 2: Security Settings")
        print("  [L] LOW (Fast, No Confirmations)")
        print("  [M] MEDIUM (Balanced - Default)")
        print("  [H] HIGH (Paranoid, Confirm Everything)")
        
        lvl = self._input("Security Level", "M").upper()
        if lvl.startswith("L"): self.config["security"]["level"] = "LOW"
        elif lvl.startswith("H"): self.config["security"]["level"] = "HIGH"
        else: self.config["security"]["level"] = "MEDIUM"

        self.config["security"]["safe_mode"] = self._bool_input("Enable Safe Mode (Prompts for dangerous actions)?", True)

    def _setup_core_features(self):
        print("\n🔹 Step 3: Core Features")
        mods = self.config["modules"]
        mods["web_search"] = self._bool_input("Enable Web Search?", True)
        mods["memory"] = self._bool_input("Enable Long-Term Memory (RAG)?", True)
        mods["planner"] = self._bool_input("Enable Complex Task Planner?", True)
        mods["skills"] = self._bool_input("Enable Skill Learning?", True)

    def _setup_communication(self):
        print("\n🔹 Step 4: Communication")
        mods = self.config["modules"]
        if self._bool_input("Enable WhatsApp Integration?", False):
            mods["whatsapp"] = True
            print("  (Note: Requires scanning QR code on first run)")
        
        if self._bool_input("Enable Gmail Integration?", False):
            mods["gmail"] = True
            self._setup_google_creds()

        if self._bool_input("Enable Google Calendar?", False):
            mods["calendar"] = True
            if not mods.get("gmail"): self._setup_google_creds() # Ask if not already asked

    def _setup_google_creds(self):
        """Helper to copy credentials.json"""
        if os.path.exists(os.path.join(Config.TESS_DIR, "credentials.json")):
            return # Already there
            
        print("  >> Path to your 'credentials.json' (from Google Cloud Console):")
        path = self._input("  Path").strip('"') # Remove quotes
        if path and os.path.exists(path):
            try:
                shutil.copy(path, os.path.join(Config.TESS_DIR, "credentials.json"))
                print("  >> Credentials copied successfully.")
            except Exception as e:
                print(f"  >> Error copying file: {e}")
        else:
            print("  >> File not found. Gmail/Calendar may not work.")

    def _setup_media_web(self):
        print("\n🔹 Step 5: Media & Web")
        mods = self.config["modules"]
        mods["media"] = self._bool_input("Enable YouTube Player?", True)
        mods["web_scraping"] = self._bool_input("Enable Web Scraping?", True)

    def _setup_ai_features(self):
        print("\n🔹 Step 6: Advanced AI Capabilities")
        adv = self.config["advanced"]
        adv["deep_research"] = self._bool_input("Enable Deep Research Agent?", True)
        adv["trip_planner"] = self._bool_input("Enable Trip Planning Agent?", True)
        adv["code_generation"] = self._bool_input("Enable Code Generation (Architect)?", True)
        adv["file_converter"] = self._bool_input("Enable File Converters?", True)
        adv["file_organizer"] = self._bool_input("Enable Intelligent File Organizer?", True)

    def _setup_integrations(self):
        print("\n🔹 Step 7: Integrations")
        integ = self.config["integrations"]
        
        if self._bool_input("Enable Telegram Bot?", False):
            integ["telegram"]["enabled"] = True
            integ["telegram"]["token"] = self._input("  Telegram Bot Token")
            integ["telegram"]["user_id"] = self._input("  Allowed User ID")

        integ["librarian"]["enabled"] = self._bool_input("Enable Librarian (Auto File Watcher)?", True)
        if integ["librarian"]["enabled"]:
             integ["librarian"]["watch_path"] = self._input("  Folder to watch (default: current)", ".")

    def _save_config(self):
        # Ensure TESS dir
        os.makedirs(Config.TESS_DIR, exist_ok=True)
        path = Config.CONFIG_PATH
        
        try:
            with open(path, 'w') as f:
                json.dump(self.config, f, indent=2)
            print(f"\nConfiguration saved to: {path}")
            # Secure it (Windows equivalent of chmod 600 is hard, usually OS handles user perms)
        except Exception as e:
            print(f"Error saving config: {e}")

if __name__ == "__main__":
    SetupWizard().run()
