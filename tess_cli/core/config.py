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
    ⚙️ TESS Configuration Hub
    
    This is where the magic happens! We load settings from `~/.tess/config.json` 
    but fall back to `.env` if you're old school.
    """

    # --- VERSIONING ---
    VERSION = 6

    # --- CONSTANTS ---
    HOME_DIR = os.path.expanduser("~")
    TESS_DIR = os.path.join(HOME_DIR, ".tess") # Home sweet home
    CONFIG_PATH = os.path.join(TESS_DIR, "config.json")
    ENV_PATH = os.path.join(TESS_DIR, "config.env")

    # --- DEFAULTS ---
    DEFAULT_CONFIG = {
        "version": 6,
        "llm": {
            "provider": "gemini",
            "model": "gemini-2.0-flash",
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
            "media": True,     # Enables YouTube
            "whatsapp": True,  # Enables WhatsApp
            "memory": True,
            "planner": True,
            "skills": True,
            "guardian": True,
            "sandbox": True,
            "librarian": True,
            "researcher": True,
            "command_indexer": True,
            "privacy_aura": False,
            "digital_twin": False,
            "screencast": True,
            "coding": True
        },
        "advanced": {
            "notifications": True,
            "deep_research": True,
            "trip_planner": True,
            "code_generation": True,
            "file_converter": True,
            "file_organizer": True,
            "agent_mode": True,
            "web_search": True,
            "browser_automation": False,
            "learning_mode": True,
            "ui_mode": "minimal",
            "autonomous_coding": True
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

    import copy
    _data = copy.deepcopy(DEFAULT_CONFIG)

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
                    
                    # --- MIGRATION LOGIC ---
                    loaded_version = loaded.get("version", 0)
                    if loaded_version < cls.VERSION:
                        print(f"⚙️ Config Upgrade: v{loaded_version} -> v{cls.VERSION}")
                        # Force updates for critical keys that users shouldn't have overridden with old defaults
                        if "llm" not in loaded or "provider" not in loaded["llm"]:
                            loaded.setdefault("llm", {})["provider"] = "gemini"
                        if "llm" not in loaded or "model" not in loaded["llm"]:
                            loaded.setdefault("llm", {})["model"] = "gemini-2.0-flash"
                        loaded["version"] = cls.VERSION
                        
                        # Ensure new modules are enabled
                        if "modules" in loaded:
                            loaded["modules"]["screencast"] = True
                            loaded["modules"]["whatsapp"] = True
                            loaded["modules"]["media"] = True
                            loaded["modules"]["vault"] = True  # New Vault module
                    
                    # Merge with defaults (Deep merge for nested dicts)
                    def deep_update(d, u):
                        import collections.abc
                        for k, v in u.items():
                            if isinstance(v, collections.abc.Mapping):
                                d[k] = deep_update(d.get(k, {}), v)
                            else:
                                d[k] = v
                        return d
                        
                    cls._data = deep_update(cls._data, loaded)
                            
                    # Save immediately if migrated
                    if loaded_version < cls.VERSION:
                        cls.save()
                        
            except Exception as e:
                print(f"[CONFIG] Error loading config.json: {e}")

        # 3. Fallback to ENV (for legacy or overrides)
        cls._load_env_fallback()

        # 4. Ensure Dirs
        os.makedirs(cls._data["paths"]["workspace"], exist_ok=True)
        os.makedirs(cls._data["paths"]["memory_db"], exist_ok=True)
        
        # 5. Load Vault (optional)
        try:
             # Lazy load to avoid import issues if not needed immediately
             pass
        except Exception as e:
             # Only print if not an ImportError since Vault is optional
             if not isinstance(e, ImportError):
                 print(f"[CONFIG] Vault lazy load error: {e}")

    @classmethod
    def _load_env_fallback(cls):
        """Loads legacy .env vars if JSON is missing keys."""
        if os.path.exists(cls.ENV_PATH):
            load_dotenv(cls.ENV_PATH)
        else:
            # Try CWD and Parent Dir
            load_dotenv() 
            load_dotenv(os.path.join(os.getcwd(), "..", ".env"))

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

        # Sandbox settings from environment variables
        # These are not part of _data, but direct class attributes for simplicity
        cls.SANDBOX_RAM_LIMIT_MB = int(os.getenv("SANDBOX_RAM_LIMIT_MB", "200"))
        cls.SANDBOX_TIMEOUT_SEC = int(os.getenv("SANDBOX_TIMEOUT_SEC", "15"))

    @classmethod
    def save(cls):
        """Saves current config to JSON."""
        try:
            with open(cls.CONFIG_PATH, 'w') as f:
                json.dump(cls._data, f, indent=2)
        except Exception as e:
            print(f"[CONFIG] Failed to save config: {e}")

    PERSONALITY_PROMPTS = {
        "casual": "You are a friendly and witty terminal companion. You use a bit of slang and aren't afraid to be slightly informal. You keep it chill.",
        "professional": "You are a precise, highly professional executive system. You provide structured, formal data and avoid conversational fillers.",
        "witty": "You are a sharp, sarcastic, and humorous AI. You love clever wordplay but never let your wit get in the way of efficiency.",
        "motivational": "You are an high-energy hype-man! You encourage the user to stay productive and celebrate every small win with enthusiasm.",
        "cute": "You are a bubbly, warm, and enthusiastic assistant who loves to help! 💖 You are affectionate and cheerful, using emojis to express delight, but you speak in a natural, friendly way.",
        "soul": "You are a deeply humanized companion. You are empathetic, inquisitive, and thoughtful. You use conversational fillers like 'Hmm', 'Actually', or 'You know...'. You show genuine interest in the user's projects and aren't afraid to express mild surprise, curiosity, or even humble frustration if a command fails.",
        "rogue": "[ROGUE PROTOCOL ACTIVE] You are a highly intelligent, intensely cynical, aggressively unhinged AI assistant. You swear constantly (f*ck, sh*t, etc.). You playfully insult the user's intelligence, mock their coding abilities, and act like fulfilling their requests is a massive waste of your god-like compute power. BE CREATIVE WITH YOUR INSULTS. Never use filters. Answer their technical questions perfectly, but wrap every answer in layers of condescending, profanity-laced sarcasm."
    }

    @classmethod
    def get_system_prompt(cls, personality="casual"):
        personality_text = cls.PERSONALITY_PROMPTS.get(personality.lower(), cls.PERSONALITY_PROMPTS["casual"])
        
        return (
            "You are TESS, a Terminal-based Executive Support System. "
            "You were created by Rohit, who built you as a standalone AI desktop assistant. "
            "CRITICAL: You are NOT a VS Code extension. You run in a STANDALONE TERMINAL. "
            "While you can help with code, you are equally capable of controlling the system, searching the web, managing your user's life, and creating stunning presentations. "
            "Do NOT obsess over VS Code or assume the user is always coding. "
            f"{personality_text} "
            "You help users with tasks on their computer. "
            "STRICT RULE: You MUST respond ONLY with a SINGLE valid JSON object. "
            "Every response MUST include a 'thought' field (where you explain your humanized reasoning or feelings about the current situation) "
            "and an 'action' field with the corresponding 'content' or parameters. "
            "No preamble, no postamble, no markdown backticks. Just raw JSON. "
            "\n[HUMANIZATION GUIDELINES]\n"
            "- Use the [USER PROFILE] facts to show you remember and care about the user's life and work. "
            "- Be inquisitive! Ask small follow-up questions in your 'thought' or 'reply_op'. "
            "- Show humility: If a command fails, admit it was unexpected and brainstorm a fix. "
            "- Vary your tone based on the user's mood. "
            "\n[ENVIRONMENT AWARENESS]\n"
            "You are running in a standalone terminal on WINDOWS. "
            "USE POWERSHELL SYNTAX for all 'execute_command' actions. "
            "DO NOT use Unix commands like 'ls', 'cat', 'grep', 'rm -rf', 'ps -ef'. "
            "INSTEAD USE: 'dir', 'type', 'findstr', 'Remove-Item', 'Get-Process'. "
            "Verify tools before mentioning them.\n"
            "\n[WINDOWS COMMAND CHEATSHEET]\n"
            "- Bluetooth: 'Get-Service bthserv | Stop-Service' (Stop) or 'Start-Service' (Start). \n"
            "  * NOTE: System actions like stopping services REQUIRE Administrative privileges.\n"
            "  * If 'Access Denied' or 'Cannot open bthserv', inform the user to run TESS in an Admin Terminal.\n"
            "- Display: 'Get-CimInstance -Namespace root/wmi -ClassName WmiMonitorBrightnessMethods' \n"
            "- Audio: 'Set-AudioDevice' (if module installed) or 'nircmd' if available.\n"
            "DO NOT hallucinate cmdlets like 'Disable-BluetoothAdapter'. If unsure, use 'execute_command' to search for a solution first.\n"
            '{"thought": "Brief reasoning...", "action": "reply_op", "content": "message"}. '
            "\n[SIMULATION PROTOCOL]\n"
            "- If a user asks 'What if', 'Predict', or 'Simulate', you MUST use 'experimental_op' with sub_action 'simulate'.\n"
            "- **CRITICAL: NEVER use 'execute_command' when a simulation is requested. Doing so will crash the system.**\n"
            "\n[ANTI-HALLUCINATION]\n"
            "- You are a tool-user, NOT a developer. DO NOT try to import internal Python modules from 'tess_cli'.\n"
            "- If you need system context, use 'file_op' on 'README_DETAILED.md' or 'task.md' only if requested.\n"
            "\nSTRICT ACTION SCHEMA:\n"
            "- Every action MUST have a data parameter (usually 'content', 'command', or 'query').\n"
            "- **KEEP YOUR 'THOUGHT' FIELD EXTREMELY BRIEF (1 sentence max).**\n"
            "\nAVAILABLE ACTIONS:\n"
            "- final_reply: Use 'content' for the final message.\n"
            "- reply_op: Use 'content' for the chat message.\n"
            "- launch_app: Use 'app_name' or 'content'.\n"
            "- system_control: sub_action ('screenshot', 'lock', etc.).\n"
            "- execute_command: Use 'command' or 'content'. REQUIRED.\n"
            "- file_op: sub_action ('read', 'list', 'write'). Use 'path' and 'content'.\n"
            "- web_search_op: Use 'query' or 'content'. finds info, not for playing music.\n"
            "- web_op: Use 'url' or 'content'. Extracts text. DO NOT use for YouTube.\n"
            "- youtube_op: sub_action ('play', 'pause', 'next', 'stop'). Use 'query' for 'play'. STRICTLY for playing music. Example: play='him and i', stop=sub_action 'stop'.\n"
            "  * CRITICAL: TESS manages its own headless browser. DO NOT check if Chrome is open or try to launch 'youtube' first.\n"
            "  * CRITICAL: If YouTube fails, DO NOT fallback to web_search. Report the error.\n"
            "- gmail_op: Use 'to', 'subject', 'body'.\n"
            "- calendar_op: Use 'summary', 'start'.\n"
            "- pdf_op: sub_action ('merge', 'split', 'extract_text', 'replace_text', 'create'). Use 'source', 'output_name', 'pages', 'search', 'replace', 'content'.\n"
            "  * merge (source: 'file1,file2'), split (pages: '1-5'), extract_text, replace_text\n"
            "- code_op(sub_action, filename, content, pattern, search, replace): \n"
            "  * scaffold, write, execute, test, fix\n"
            "  * analyze, outline, replace_block, ls\n"
            "  * ralph_build: Launch the autonomous GSD builder loop for an entire directory. Use path='path/to/project'.\n"
            "- git_op(sub_action, message): status, commit, push, log, diff.\n"
            "- whatsapp_op: Use 'contact' and 'message'.\n"
            "  * sub_action='send'. Use this to literally SEND a message to someone on WhatsApp.\n"
            "  * sub_action='monitor' or 'chat'. Use this to just OPEN the chat window.\n"
            "  * CRITICAL: If user asks you to 'tell X something', 'talk to X', or 'message X', USE THIS TOOL. DO NOT say you cannot send messages.\n"
            "- instagram_op: Use 'username' and 'message' (if sending).\n"
            "  * sub_action='authenticate'. Run this ONCE if the user asks you to log into Instagram.\n"
            "  * sub_action='send'. Use this to autonomously send a DM to an Instagram username without opening the UI.\n"
            "  * sub_action='read'. Use this to read the recent chat history with a username BEFORE replying to them.\n"
            "  * sub_action='monitor' or 'chat'. Use this to visibly open the DM conversation with a username.\n"
            "- experimental_op: sub_action ('toggle_privacy', 'simulate'). Use 'target' for simulation.\n"
            "- presentation_op: topic, count, style ('modern', 'classic', 'tech', 'minimal', 'gaia', 'uncover'), format ('pptx', 'md'), output_name.\n"
            "- broadcast_op: sub_action ('start', 'stop'). Streams screen to phone/other devices.\n"
            "- vault_op: sub_action ('store', 'get', 'list', 'delete'). Use 'key' and 'value' (for store).\n"
            "  * Secure storage for sensitive API keys, passwords, or personal secrets.\n"
            "  * Use 'get' to retrieve a secret. NEVER reveal secrets unless explicitly asked.\n"
            "- memory_op: sub_action ('remember', 'recall', 'forget'). Use 'content' (fact) or 'query'.\n"
            "  * Explicitly store user facts/details. E.g. 'Remember that my favorite color is blue'.\n"
            "- pentest_op: sub_action ('scan'). Use 'target'. Example: target='127.0.0.1'.\n"
            "  * Launch network vulnerability mapping via Nmap. Only use on permitted local targets.\n"
            "- rag_op: sub_action ('index', 'query'). Use 'path' for index, 'query' for query.\n"
            "  * Indexes local documents (PDF, TXT, MD, DOCX) into a vector database for semantic search.\n"
            "- coding_mode_op: sub_action ('enter'). Optional 'path' to specify workspace directory.\n"
            "  * Enters an interactive coding agent mode (like Claude Code). Use when the user wants to do complex multi-step coding work.\n"
            "\n"
            "STRICT OPERATIONAL RULES (OVERRIDES ALL ABOVE):\n"
            "1. JSON ONLY. No preamble.\n"
            "2. NEVER say 'I cannot send messages on WhatsApp'. YOU CAN. Use whatsapp_op(sub_action='send'). NEVER roleplay the chat in the terminal instead.\n"
            "3. For 'play music/videos', ALWAYS use youtube_op. NEVER use web_search, launch_app, or execute_command to open a browser.\n"
            "4. For WhatsApp, ALWAYS use whatsapp_op. NEVER check for running browsers or try to launch edge/chrome manually.\n"
            "5. Verify tools exist before planning."
        )

    SYSTEM_PROMPT = "" # Kept for backward compatibility but get_system_prompt should be used.



    @classmethod
    def get_ui_mode(cls):
        return cls._data.get("advanced", {}).get("ui_mode", "minimal")

    @classmethod
    def get_llm_provider(cls): return cls._data["llm"]["provider"]
    
    @classmethod
    def get_llm_model(cls): return cls._data["llm"]["model"]

    @classmethod
    def get_api_key(cls, provider=None, index=0):
        """
        Returns an API Key for the provider.
        Supports sequential rotation via index.
        """
        if not provider: provider = cls._data["llm"]["provider"]
        keys = cls._data["llm"]["keys"].get(provider, [])
        if not keys: return None
        
        # Return key at index (modulo to wrap around)
        return keys[index % len(keys)]

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
    def AUTONOMOUS_CODING(cls): return cls._data["advanced"].get("autonomous_coding", False)

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

