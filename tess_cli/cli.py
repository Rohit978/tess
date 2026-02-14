import sys
import os
import warnings

# Suppress annoying warnings
warnings.filterwarnings("ignore", category=FutureWarning, module="google.api_core")
warnings.filterwarnings("ignore", message=".*google.generativeai.*")
warnings.filterwarnings("ignore", category=FutureWarning, message=".*Python version.*")

print("\r[TESS] Powering up systems...", end="", flush=True)
import time
time.sleep(0.1)

# Add paths
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from .core.profile_manager import ProfileManager
from .core.orchestrator import process_action
from .core.logger import setup_logger
import threading

# Components
from .core.executor import Executor
from .core.config import Config
from .core.app_launcher import AppLauncher
from .core.browser_controller import BrowserController
from .core.system_controller import SystemController
from .core.file_manager import FileManager
from .core.knowledge_base import KnowledgeBase
from .core.planner import Planner
from .core.web_browser import WebBrowser
from .core.task_registry import TaskRegistry
from .core.whatsapp_client import WhatsAppClient
from .core.youtube_client import YouTubeClient
from .core.voice_client import VoiceClient
from .core.organizer import Organizer
from .core.google_client import GoogleClient
from .core.architect import Architect
from .core.security import SecurityEngine
from .core.command_indexer import CommandIndexer
from .core.librarian import Librarian
from .core.scheduler import TessScheduler
from .skills.sysadmin import SysAdminSkill

logger = setup_logger("Main")

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
            web_browser=valid_comps.get('web_search'), # Key mismatch fix
            task_registry=valid_comps.get('task_registry'),
            whatsapp_client=valid_comps.get('whatsapp'),
            youtube_client=valid_comps.get('youtube_client'),
            executor=valid_comps.get('executor')
        )
        bot.run()
    except Exception as e:
        logger.error(f"Telegram Bot failed: {e}")

def main():
    # 0. Check for Setup/Init
    if len(sys.argv) > 1 and sys.argv[1].lower() == "init":
        from .core.setup_wizard import SetupWizard
        SetupWizard().run()
        return

    print("--------------------------------------------------")
    print("  TESS TERMINAL PRO - HYBRID AGENT (v5.0)")
    print("--------------------------------------------------")
    
    # Init Core
    knowledge_db = KnowledgeBase() if Config.is_module_enabled("memory") else None
    profiles = ProfileManager(knowledge_db=knowledge_db)
    
    executor = Executor(safe_mode=Config.SAFE_MODE)
    security = SecurityEngine(level=Config.get_security_level())
    
    brain = profiles.get_brain("terminal_user")
    
    # Initialize Components with Toggles
    # ----------------------------------
    comps = {}
    
    # Core (Always On)
    comps['brain'] = brain
    comps['executor'] = executor
    comps['security'] = security
    comps['launcher'] = AppLauncher()
    comps['sys_ctrl'] = SystemController()
    comps['file_mgr'] = FileManager()
    comps['task_registry'] = TaskRegistry()
    comps['browser_ctrl'] = BrowserController()
    comps['sysadmin'] = SysAdminSkill()
    comps['command_indexer'] = CommandIndexer(knowledge_db)
    
    # Conditional Modules
    comps['knowledge_db'] = knowledge_db
    
    # Planner
    if Config.is_module_enabled("planner"):
        comps['planner'] = Planner(brain)
    else:
        comps['planner'] = None

    # Web Search
    if Config.is_module_enabled("web_search") or Config.is_module_enabled("web_scraping"):
        comps['web_search'] = WebBrowser(headless=True)
    else:
        comps['web_search'] = None

    # WhatsApp
    if Config.is_module_enabled("whatsapp"):
        # Requires Voice?
        vc = VoiceClient(model_size="base") # Lightweight
        comps['whatsapp'] = WhatsAppClient(brain, voice_client=vc, headless=False)
    else:
        comps['whatsapp'] = None

    # Voice
    comps['voice_client'] = VoiceClient(model_size="base")

    # YouTube
    if Config.is_module_enabled("media"):
        comps['youtube_client'] = YouTubeClient(headless=False)
    else:
        comps['youtube_client'] = None

    # Organizer
    if Config.is_module_enabled("file_organizer"):
        comps['organizer'] = Organizer(brain)
    else:
        comps['organizer'] = None

    # Code Gen
    if Config.is_module_enabled("code_generation"):
        comps['architect'] = Architect()
    else:
        comps['architect'] = None
        
    # Google (Gmail/Cal)
    if Config.is_module_enabled("gmail") or Config.is_module_enabled("calendar"):
         comps['google_client'] = GoogleClient()
    else:
         comps['google_client'] = None

    # Librarian
    if Config._data["integrations"]["librarian"]["enabled"]:
        watch_path = Config._data["integrations"]["librarian"]["watch_path"]
        if watch_path == ".": watch_path = os.getcwd()
        
        librarian = Librarian(knowledge_db, watch_path=watch_path)
        print("📚 Librarian (Active Learning) starting...")
        librarian.start()
    else:
        librarian = None

    # Scheduler
    tess_scheduler = TessScheduler(brain=brain)
    tess_scheduler.start()
    
    # Telegram
    if Config._data["integrations"]["telegram"]["enabled"] and Config.TELEGRAM_BOT_TOKEN:
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
