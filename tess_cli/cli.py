import sys
import os
import warnings
import time
import threading

# Suppress annoying warnings
warnings.filterwarnings("ignore", category=FutureWarning, module="google.api_core")
warnings.filterwarnings("ignore", message=".*google.generativeai.*")
warnings.filterwarnings("ignore", category=FutureWarning, message=".*Python version.*")

# Lazy Imports handled in main() to prevent startup crashes (e.g. ChromaDB/Pydantic issues)

def setup_logger_local(name):
    # Minimal logger setup if core logger fails
    import logging
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger

logger = setup_logger_local("Main")

def start_telegram_bot(profiles, components):
    """Runs the Telegram Bot in a separate thread."""
    try:
        from .interfaces.telegram_bot import TessBot
        # Filter None components
        valid_comps = {k: v for k, v in components.items() if v is not None}
        
        bot = TessBot(
            profile_manager=profiles,
            launcher=valid_comps.get('launcher'),
            browser_ctrl=valid_comps.get('browser_ctrl'),
            sys_ctrl=valid_comps.get('sys_ctrl'),
            file_mgr=valid_comps.get('file_mgr'),
            knowledge_db=valid_comps.get('knowledge_db'),
            planner=valid_comps.get('planner'),
            web_browser=valid_comps.get('web_search'),
            task_registry=valid_comps.get('task_registry'),
            whatsapp_client=valid_comps.get('whatsapp'),
            youtube_client=valid_comps.get('youtube_client'),
            executor=valid_comps.get('executor')
        )
        bot.run()
    except Exception as e:
        logger.error(f"Telegram Bot failed: {e}")

def main():
    # 0. Check for Setup/Init (FAST EXIT)
    if len(sys.argv) > 1 and sys.argv[1].lower() == "init":
        try:
            from .core.setup_wizard import SetupWizard
            SetupWizard().run()
        except ImportError as e:
            print(f"[ERROR] Could not load Setup Wizard: {e}")
            print("Ensure dependencies are installed: pip install -r requirements.txt")
        return

    print("--------------------------------------------------")
    print("  TESS TERMINAL PRO - HYBRID AGENT (v5.0)")
    print("--------------------------------------------------")
    print("\r[TESS] Powering up systems...", end="", flush=True)
    time.sleep(0.1)

    # Add paths
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))

    # 1. Import ESSENTIAL modules (these MUST work)
    try:
        from .core.profile_manager import ProfileManager
        from .core.orchestrator import process_action
        from .core.logger import setup_logger
        from .core.executor import Executor
        from .core.config import Config
        from .core.security import SecurityEngine
        
        global logger
        logger = setup_logger("Main")
    except Exception as e:
        print(f"\n\n[CRITICAL ERROR] Failed to import essential modules: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # 2. Import OPTIONAL modules individually (each can fail without killing TESS)
    def safe_import(module_path, class_name):
        """Import a class, return None if it fails."""
        try:
            mod = __import__(module_path, fromlist=[class_name], globals=globals())
            return getattr(mod, class_name)
        except Exception as e:
            print(f"  ⚠ {class_name} unavailable: {e}")
            return None

    AppLauncher = safe_import("tess_cli.core.app_launcher", "AppLauncher")
    BrowserController = safe_import("tess_cli.core.browser_controller", "BrowserController")
    SystemController = safe_import("tess_cli.core.system_controller", "SystemController")
    FileManager = safe_import("tess_cli.core.file_manager", "FileManager")
    KnowledgeBase = safe_import("tess_cli.core.knowledge_base", "KnowledgeBase")
    Planner = safe_import("tess_cli.core.planner", "Planner")
    WebBrowser = safe_import("tess_cli.core.web_browser", "WebBrowser")
    TaskRegistry = safe_import("tess_cli.core.task_registry", "TaskRegistry")
    WhatsAppClient = safe_import("tess_cli.core.whatsapp_client", "WhatsAppClient")
    YouTubeClient = safe_import("tess_cli.core.youtube_client", "YouTubeClient")
    VoiceClient = safe_import("tess_cli.core.voice_client", "VoiceClient")
    Organizer = safe_import("tess_cli.core.organizer", "Organizer")
    GoogleClient = safe_import("tess_cli.core.google_client", "GoogleClient")
    Architect = safe_import("tess_cli.core.architect", "Architect")
    CommandIndexer = safe_import("tess_cli.core.command_indexer", "CommandIndexer")
    Librarian = safe_import("tess_cli.core.librarian", "Librarian")
    TessScheduler = safe_import("tess_cli.core.scheduler", "TessScheduler")
    SysAdminSkill = safe_import("tess_cli.skills.sysadmin", "SysAdminSkill")
    print()  # Newline after warnings

    # Init Core
    knowledge_db = KnowledgeBase() if KnowledgeBase and Config.is_module_enabled("memory") else None
    profiles = ProfileManager(knowledge_db=knowledge_db)
    
    executor = Executor(safe_mode=Config.SAFE_MODE)
    security = SecurityEngine(level=Config.get_security_level())
    
    brain = profiles.get_brain("terminal_user")
    
    # Initialize Components with Toggles
    # ----------------------------------
    comps = {}
    
    # Core (create if class available)
    comps['brain'] = brain
    comps['executor'] = executor
    comps['security'] = security
    comps['launcher'] = AppLauncher() if AppLauncher else None
    comps['sys_ctrl'] = SystemController() if SystemController else None
    comps['file_mgr'] = FileManager() if FileManager else None
    comps['task_registry'] = TaskRegistry() if TaskRegistry else None
    comps['browser_ctrl'] = BrowserController() if BrowserController else None
    comps['sysadmin'] = SysAdminSkill() if SysAdminSkill else None
    comps['command_indexer'] = CommandIndexer(knowledge_db) if CommandIndexer else None
    
    # Conditional Modules
    comps['knowledge_db'] = knowledge_db
    
    # Planner
    if Planner and Config.is_module_enabled("planner"):
        comps['planner'] = Planner(brain)
    else:
        comps['planner'] = None

    # Web Search
    if WebBrowser and (Config.is_module_enabled("web_search") or Config.is_module_enabled("web_scraping")):
        comps['web_search'] = WebBrowser(headless=True)
    else:
        comps['web_search'] = None

    # WhatsApp
    if WhatsAppClient and Config.is_module_enabled("whatsapp"):
        vc = VoiceClient(model_size="base") if VoiceClient else None
        comps['whatsapp'] = WhatsAppClient(brain, voice_client=vc, headless=False)
    else:
        comps['whatsapp'] = None

    # Voice
    comps['voice_client'] = VoiceClient(model_size="base") if VoiceClient else None

    # YouTube
    if YouTubeClient and Config.is_module_enabled("media"):
        comps['youtube_client'] = YouTubeClient(headless=False)
    else:
        comps['youtube_client'] = None

    # Organizer
    if Organizer and Config.is_module_enabled("file_organizer"):
        comps['organizer'] = Organizer(brain)
    else:
        comps['organizer'] = None

    # Code Gen
    if Architect and Config.is_module_enabled("code_generation"):
        comps['architect'] = Architect()
    else:
        comps['architect'] = None
        
    # Google (Gmail/Cal)
    if GoogleClient and (Config.is_module_enabled("gmail") or Config.is_module_enabled("calendar")):
         comps['google_client'] = GoogleClient()
    else:
         comps['google_client'] = None

    # Librarian
    librarian = None
    if Librarian and Config._data.get("integrations", {}).get("librarian", {}).get("enabled", False):
        watch_path = Config._data["integrations"]["librarian"].get("watch_path", ".")
        if watch_path == ".": watch_path = os.getcwd()
        
        librarian = Librarian(knowledge_db, watch_path=watch_path)
        print("📚 Librarian (Active Learning) starting...")
        librarian.start()

    # Scheduler
    if TessScheduler:
        tess_scheduler = TessScheduler(brain=brain)
        tess_scheduler.start()
    
    # Telegram
    if Config.TELEGRAM_BOT_TOKEN and Config._data.get("integrations", {}).get("telegram", {}).get("enabled", False):
        print("🤖 Starting Telegram...")
        threading.Thread(target=start_telegram_bot, args=(profiles, comps), daemon=True).start()

    print("--------------------------------------------------")
    print("  CLI ACCESS MODE (Type 'exit' to quit)")
    print("--------------------------------------------------")
    
    while True:
        try:
            user_input = input("\n[USER]> ").strip()
            if not user_input: continue
            if user_input.lower() in ["exit", "quit"]: break

            # Direct Commands
            if user_input.lower() == "learn apps":
                comps['executor'].scan_installed_apps()
                continue
            
            if user_input.lower() == "learn commands":
                print("\n[TESS] Starting Command Indexing...")
                res = comps['command_indexer'].index_system_commands()
                print(f"[TESS] {res}")
                continue

            if user_input.lower().startswith("watch ") and librarian:
                path = user_input[6:].strip()
                if path == ".": path = os.getcwd()
                success, msg = librarian.change_watch_path(path)
                print(f"[LIBRARIAN] {msg}")
                continue
            
            # Voice Input
            if user_input.lower() in ["listen", "voice"]:
                path = comps['voice_client'].listen()
                if path:
                    txt = comps['voice_client'].transcribe(path)
                    print(f"You said: {txt}")
                    if txt: user_input = txt
                    else: continue

            # 1. GENERATE
            print("Thinking...")
            response = brain.generate_command(user_input)
            
            # 2. SECURITY CHECK
            is_safe, reason = security.validate_action(response)
            if not is_safe:
                print(f"🛡️ [SECURITY BLOCK] {reason}")
                brain.update_history("system", f"Action BLOCKED: {reason}")
                continue

            # 3. EXECUTE
            process_action(response, comps, brain)

        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"CRITICAL ERROR: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()
