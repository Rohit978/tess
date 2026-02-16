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
        import copy
        Config.load()
        self.config = copy.deepcopy(Config._data)
        
        # Ensure keys structure exists
        if "keys" not in self.config["llm"]:
            self.config["llm"]["keys"] = {
                "groq": [],
                "openai": [],
                "deepseek": [],
                "gemini": []
            }

    def _setup_personalization(self):
        print("\n🔹 Step 9: Personalization & UI")
        
        # 1. UI Mode
        print("\nSelect UI Mode:")
        print("  [1] Minimal (Clean, Fast)")
        print("  [2] Rich (Panels, heavy)")
        ui_choice = self._input("Choice", "1")
        self.config["advanced"]["ui_mode"] = "minimal" if ui_choice == "1" else "rich"
        
        # 2. Notifications
        self.config["advanced"]["notifications"] = self._bool_input("Enable Windows Toast Notifications?", True)
        
        # 3. Personality (Updates UserProfile)
        try:
            from .user_profile import UserProfile
            profile = UserProfile()
            
            print("\nSelect TESS Personality:")
            print("  [1] Casual (Default)")
            print("  [2] Professional (Concise)")
            print("  [3] Hype-Man (Motivational)")
            print("  [4] Cate/Warm (Friendly)")
            print("  [5] Soul (Empathetic)")
            
            p_map = {"1": "casual", "2": "professional", "3": "motivational", "4": "cute", "5": "soul"}
            p_choice = self._input("Choice", "1")
            
            new_persona = p_map.get(p_choice, "casual")
            profile.personality = new_persona
            profile.save()
            print(f"  >> Personality set to: {new_persona.upper()}")
            
        except Exception as e:
            print(f"  [Warning] Could not update UserProfile: {e}")

    def run(self):
        print("\n🧙‍♂️  TESS TERMINAL PRO - SETUP WIZARD (v5.0)")
        print("==========================================")
        
        while True:
            print("\nMAIN MENU:")
            print("  [1] Intelligence Engine (LLM Keys/Models)")
            print("  [2] Security Settings")
            print("  [3] Core Features (Memory, Web, etc.)")
            print("  [4] Communication (WhatsApp, Gmail)")
            print("  [5] Media & Web (YouTube, Scraping)")
            print("  [6] Advanced AI (Research, Coding)")
            print("  [7] Integrations (Telegram, Librarian)")
            print("  [8] Experimental Protocol (Guardian, Sandbox)")
            print("  [9] Personalization (UI, Notifications, Persona)")
            print("  [F] Run Full Setup Wizard (Linear)")
            print("  [0] Save & Exit")
            
            choice = self._input("\nSelect Option", "0").upper()
            
            if choice == "1": self._setup_llm()
            elif choice == "2": self._setup_security()
            elif choice == "3": self._setup_core_features()
            elif choice == "4": self._setup_communication()
            elif choice == "5": self._setup_media_web()
            elif choice == "6": self._setup_ai_features()
            elif choice == "7": self._setup_integrations()
            elif choice == "8": self._setup_experimental_protocol()
            elif choice == "9": self._setup_personalization()
            elif choice == "F": self.run_full_setup()
            elif choice == "0": 
                self._save_config()
                print("\n✅ Configuration Saved. Run 'tess' to start.")
                break
            else:
                print("Invalid choice. Try again.")

    def run_full_setup(self):
        """Runs the complete linear wizard."""
        print("\n🚀 Starting Full Setup...")
        self._setup_llm()
        self._setup_security()
        self._setup_core_features()
        self._setup_communication()
        self._setup_media_web()
        self._setup_ai_features()
        self._setup_integrations()
        self._setup_experimental_protocol()
        self._setup_personalization()

    def _save_config(self):
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
        existing_keys = self.config["llm"]["keys"].get(provider, [])
        current_keys_str = ",".join(existing_keys)
        print(f"\nEnter API Keys for {provider.upper()}.")
        print("You can paste a comma-separated list (key1,key2) or enter them one by one.")
        
        # First prompt shows existing keys as default
        prompt = f"{provider.title()} API Keys"
        keys_input = self._input(prompt, current_keys_str)
        
        if keys_input:
            # Handle potential list and add to temporary list
            new_keys = [k.strip() for k in keys_input.split(",") if k.strip()]
            self.config["llm"]["keys"][provider] = new_keys
            
            # Loop for "one-by-one" additions
            while self._bool_input(f"Add another {provider} key for rotation?", False):
                more_key = self._input(f"Next {provider} Key").strip()
                if more_key:
                    # Support list even in the "one-by-one" prompt
                    for sub_key in [k.strip() for k in more_key.split(",") if k.strip()]:
                        if sub_key not in self.config["llm"]["keys"][provider]:
                            self.config["llm"]["keys"][provider].append(sub_key)
                else: break
        
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

    def _setup_experimental_protocol(self):
        print("\n☢️  Step 8: Experimental Protocol (Use with caution)")
        mods = self.config["modules"]
        mods["privacy_aura"] = self._bool_input("Enable Privacy Aura (Guardian - Face/Stranger Detection)?", False)
        mods["digital_twin"] = self._bool_input("Enable Digital Twin (Multiverse Sandbox - Predictive Safety)?", False)

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
