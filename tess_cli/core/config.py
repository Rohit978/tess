import os
import json
import random
from dotenv import load_dotenv


class classproperty:
    """Descriptor for class-level properties (accessed as Config.X without instantiation)."""
    def __init__(self, func):
        self.fget = func
    def __get__(self, obj, owner):
        return self.fget(owner)


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

    SYSTEM_PROMPT = (
        "You are TESS, a Terminal-based Executive Support System. "
        "You are an advanced AI assistant that helps users with tasks on their computer. "
        "You MUST respond ONLY in valid JSON with an 'action' field. "
        "For ANY conversational reply (greetings, questions, answers, chit-chat), use: "
        '{"action": "reply_op", "content": "your message here"}. '
        "VALID ACTIONS: "
        'reply_op (for ALL conversation/replies), '
        'launch_app (app_name), '
        'system_control (sub_action: shutdown/restart/sleep/lock/type/press/screenshot), '
        'execute_command (command), '
        'file_op (sub_action: read/write/list, path, content), '
        'web_search_op (query), '
        'web_op (url), '
        'youtube_op (sub_action: play, query), '
        'whatsapp_op (sub_action: send/monitor, contact, message), '
        'organize_op (path), '
        'code_op (task, language). '
        "IMPORTANT: If what the user wants doesn't map to a specific action above, "
        'ALWAYS use reply_op to respond conversationally. '
        "Never invent new action names."
    )


    @classmethod
    def get_llm_provider(cls): return cls._data["llm"]["provider"]
    
    @classmethod
    def get_llm_model(cls): return cls._data["llm"]["model"]

    @classmethod
    def get_api_key(cls, provider=None):
        """
        Returns an API Key for the provider.
        Implements Key Rotation (Random choice).
        """
        if not provider: provider = cls._data["llm"]["provider"]
        keys = cls._data["llm"]["keys"].get(provider, [])
        if not keys: return None
        return random.choice(keys)

    @classmethod
    def is_module_enabled(cls, module_name):
        # Check both modules and advanced sections
        if cls._data["modules"].get(module_name, False):
            return True
        if cls._data.get("advanced", {}).get(module_name, False):
            return True
        return False

    @classmethod
    def get_security_level(cls):
        return cls._data["security"]["level"]

    # Class-level properties (accessed as Config.SAFE_MODE, Config.TELEGRAM_BOT_TOKEN, etc.)
    @classproperty
    def SAFE_MODE(cls): return cls._data["security"]["safe_mode"]

    @classproperty
    def TELEGRAM_BOT_TOKEN(cls): return cls._data["integrations"]["telegram"]["token"]
    
    @classproperty
    def TELEGRAM_ALLOWED_USER_ID(cls): return cls._data["integrations"]["telegram"]["user_id"]

    @classproperty
    def WORKSPACE_DIR(cls): return cls._data["paths"]["workspace"]
    
    @classproperty
    def MEMORY_DB_PATH(cls): return cls._data["paths"]["memory_db"]

    @classproperty
    def LLM_PROVIDER(cls): return cls._data["llm"]["provider"]

    @classproperty
    def LLM_MODEL(cls): return cls._data["llm"]["model"]

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

