import os
import json
import random
from dotenv import load_dotenv

class Config:
    """
    Advanced Configuration for TESS (v5.0)
    Loads from ~/.tess/config.json with .env fallback.
    """

    # --- CONSTANTS ---
    HOME_DIR = os.path.expanduser("~")
    TESS_DIR = os.path.join(HOME_DIR, ".tess")
    CONFIG_PATH = os.path.join(TESS_DIR, "config.json")
    ENV_PATH = os.path.join(TESS_DIR, "config.env")

    # --- DEFAULTS ---
    DEFAULT_CONFIG = {
        "llm": {
            "provider": "groq",
            "model": "llama-3.3-70b-versatile",
            "keys": {
                "groq": [],
                "openai": [],
                "deepseek": [],
                "gemini": []
            }
        },
        "security": {
            "level": "MEDIUM",  # LOW, MEDIUM, HIGH
            "safe_mode": True
        },
        "modules": {
            "web_search": True,
            "memory": True,
            "planner": True,
            "skills": True,
            "whatsapp": False,
            "gmail": False,
            "calendar": False,
            "media": True,
            "web_scraping": True
        },
        "advanced": {
            "deep_research": True,
            "trip_planner": True,
            "code_generation": True,
            "file_converter": True,
            "file_organizer": True
        },
        "integrations": {
            "telegram": {
                "enabled": False,
                "token": "",
                "user_id": ""
            },
            "librarian": {
                "enabled": True,
                "watch_path": "."
            }
        },
        "paths": {
            "workspace": os.path.join(TESS_DIR, "workspace"),
            "memory_db": os.path.join(TESS_DIR, "vector_db")
        }
    }

    _data = DEFAULT_CONFIG.copy()

    @classmethod
    def load(cls):
        """Loads configuration from JSON or Env."""
        # 1. Ensure TESS Dir exists
        os.makedirs(cls.TESS_DIR, exist_ok=True)

        # 2. Try JSON Load
        if os.path.exists(cls.CONFIG_PATH):
            try:
                with open(cls.CONFIG_PATH, 'r') as f:
                    loaded = json.load(f)
                    # Merge with defaults (shallow merge for top keys)
                    for k, v in loaded.items():
                        if k in cls._data and isinstance(v, dict):
                            cls._data[k].update(v)
                        else:
                            cls._data[k] = v
            except Exception as e:
                print(f"[CONFIG] Error loading config.json: {e}")

        # 3. Fallback to ENV (for legacy or overrides)
        # We only override if JSON didn't provide keys
        cls._load_env_fallback()

        # 4. Ensure Dirs
        os.makedirs(cls._data["paths"]["workspace"], exist_ok=True)
        os.makedirs(cls._data["paths"]["memory_db"], exist_ok=True)

    @classmethod
    def _load_env_fallback(cls):
        """Loads legacy .env vars if JSON is missing keys."""
        if os.path.exists(cls.ENV_PATH):
            load_dotenv(cls.ENV_PATH)
        else:
            load_dotenv() # Local .env

        # Helper to add if missing
        def add_key(provider, env_var):
            if not cls._data["llm"]["keys"][provider]:
                val = os.getenv(env_var)
                if val:
                    # Support comma separated in env
                    cls._data["llm"]["keys"][provider] = [k.strip() for k in val.split(",") if k.strip()]

        add_key("groq", "GROQ_API_KEY")
        add_key("openai", "OPENAI_API_KEY")
        add_key("gemini", "GEMINI_API_KEY")
        add_key("deepseek", "DEEPSEEK_API_KEY")

        # Provider fallback
        if cls._data["llm"]["provider"] == "groq" and not cls._data["llm"]["keys"]["groq"]:
             prov = os.getenv("LLM_PROVIDER")
             if prov: cls._data["llm"]["provider"] = prov

        # Telegram
        if not cls._data["integrations"]["telegram"]["token"]:
            token = os.getenv("TELEGRAM_BOT_TOKEN")
            if token:
                cls._data["integrations"]["telegram"]["enabled"] = True
                cls._data["integrations"]["telegram"]["token"] = token
                cls._data["integrations"]["telegram"]["user_id"] = os.getenv("TELEGRAM_ALLOWED_USER_ID", "")

    @classmethod
    def save(cls):
        """Saves current config to JSON."""
        try:
            with open(cls.CONFIG_PATH, 'w') as f:
                json.dump(cls._data, f, indent=2)
        except Exception as e:
            print(f"[CONFIG] Failed to save config: {e}")

    # --- ACCESSORS ---

    @property
    def LLM_PROVIDER(self): return self._data["llm"]["provider"]
    
    @property
    def LLM_MODEL(self): return self._data["llm"]["model"]

    @classmethod
    def get_api_key(cls, provider=None):
        """
        Returns an API Key for the provider.
        Implements Key Rotation (Random choice for now, or round-robin).
        """
        if not provider: provider = cls._data["llm"]["provider"]
        keys = cls._data["llm"]["keys"].get(provider, [])
        if not keys: return None
        return random.choice(keys)

    @classmethod
    def is_module_enabled(cls, module_name):
        return cls._data["modules"].get(module_name, False)

    @classmethod
    def get_security_level(cls):
        return cls._data["security"]["level"]

    @property
    def SAFE_MODE(self): return self._data["security"]["safe_mode"]

    @property
    def TELEGRAM_BOT_TOKEN(self): return self._data["integrations"]["telegram"]["token"]
    
    @property
    def TELEGRAM_ALLOWED_USER_ID(self): return self._data["integrations"]["telegram"]["user_id"]

    @property
    def WORKSPACE_DIR(self): return self._data["paths"]["workspace"]
    
    @property
    def MEMORY_DB_Path(self): return self._data["paths"]["memory_db"]

    # --- STATIC HELPERS (Legacy Support) ---
    @staticmethod
    def get_desktop_path():
        user_home = os.path.expanduser("~")
        onedrive_desktop = os.path.join(user_home, "OneDrive", "Desktop")
        if os.path.exists(onedrive_desktop): return onedrive_desktop
        return os.path.join(user_home, "Desktop")

    @staticmethod
    def get_downloads_path():
        return os.path.join(os.path.expanduser("~"), "Downloads")

# Initialize Load
Config.load()
