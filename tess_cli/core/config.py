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

    PERSONALITY_PROMPTS = {
        "casual": "You are friendly, witty, and helpful. You keep it chill and use a bit of slang and emojis when appropriate. You have a confident, laid-back personality.",
        "professional": "You are formal, precise, and highly professional. You avoid emojis and slang. You provide clear, concise, and structured responses.",
        "witty": "You are clever, sarcastic, and humorous. You love a good pun or a sharp observation, but you always remain helpful and efficient.",
        "motivational": "You are encouraging, high-energy, and motivational. You act as a hype-man for the user, pushing them to crush their goals and stay productive."
    }

    @classmethod
    def get_system_prompt(cls, personality="casual"):
        personality_text = cls.PERSONALITY_PROMPTS.get(personality.lower(), cls.PERSONALITY_PROMPTS["casual"])
        
        return (
            "You are TESS, a Terminal-based Executive Support System. "
            "You were created by Rohit, a developer who built you as a powerful AI desktop assistant. "
            f"{personality_text} "
            "You help users with tasks on their computer. "
            "STRICT RULE: You MUST respond ONLY with a SINGLE valid JSON object. "
            "No preamble, no postamble, no markdown blocks, no lists. Just the object. "
            "For ALL conversational replies, use: "
            '{"action": "reply_op", "content": "message"}. '
            "\nAVAILABLE ACTIONS:\n"
            "- reply_op(content): For greetings, chat, and info.\n"
            "- launch_app(app_name): Open applications.\n"
            "- system_control(sub_action): shutdown, restart, sleep, lock, type, press, screenshot.\n"
            "- execute_command(command): Run terminal commands.\n"
            "- file_op(sub_action, path, content): read, write, list.\n"
            "- web_search_op(query): Search Google.\n"
            "- web_op(url): Open/Scrape URLs.\n"
            "- youtube_op(sub_action, query): play.\n"
            "- whatsapp_op(sub_action, contact, message): send, monitor.\n"
            "- organize_op(path): Organize files.\n"
            "- planner_op(goal): For complex, multi-step tasks or projects.\n"
            "- code_op(sub_action, filename, content, project_type): scaffold, write, execute, test, fix, analyze, summarize.\n"
            "\nREMEMBER: If a task is complex or involves a new project, use planner_op(goal) first. "
            "Otherwise, use the specific action directly."
        )

    SYSTEM_PROMPT = "" # Kept for backward compatibility but get_system_prompt should be used.



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

