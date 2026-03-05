import sys
import os
import warnings
import time
import threading
import logging

# Suppress annoying warnings
warnings.filterwarnings("ignore", category=FutureWarning, module="google.api_core")
warnings.filterwarnings("ignore", message=".*google.generativeai.*")

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from .core.terminal_ui import (
    print_banner, boot_sequence, print_provider_info, print_ready, get_prompt,
    print_thinking, clear_thinking, print_tess_action, print_error, 
    print_warning, print_success, print_info, print_goodbye, print_help, 
    print_greeting, print_fact_learned, print_stats_dashboard, console
)

from .core.user_profile import UserProfile
from .core.profile_manager import ProfileManager
from .core.orchestrator import process_action
from .core.logger import setup_logger
from .core.executor import Executor
from .core.config import Config
from .core.security import SecurityEngine

# Components
from .core.app_launcher import AppLauncher
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
from .core.coding_engine import CodingEngine
from .core.coding_agent import CodingAgent
from .core.command_indexer import CommandIndexer
from .core.researcher import Researcher
from .core.librarian import Librarian
from .core.scheduler import TessScheduler
from .core.guardian import Guardian
from .core.sandbox import Sandbox
from .core.ralph_loop import RalphOrchestrator

# Skills
from .skills.project_director import ProjectDirector
from .skills.sysadmin import SysAdminSkill
from .skills.pdf_skill import PDFSkill
from .skills.presentation_skill import PresentationSkill

logger = setup_logger("Main")

def start_telegram_bot(profiles, components, screencast=None):
    """Runs the Telegram Bot in a separate thread."""
    try:
        from .interfaces.telegram_bot import TessBot
        valid_comps = {k: v for k, v in components.items() if v is not None}
        
        bot = TessBot(
            profile_manager=profiles,
            launcher=valid_comps.get('launcher'),
            sys_ctrl=valid_comps.get('sys_ctrl'),
            file_mgr=valid_comps.get('file_mgr'),
            knowledge_db=valid_comps.get('knowledge_db'),
            planner=valid_comps.get('planner'),
            web_browser=valid_comps.get('web_search'),
            task_registry=valid_comps.get('task_registry'),
            whatsapp=valid_comps.get('whatsapp'),
            youtube_client=valid_comps.get('youtube_client'),
            executor=valid_comps.get('executor'),
            screencast=screencast
        )
        
        while True:
            try:
                bot.run()
                break # Normal exit
            except Exception as loop_e:
                logger.error(f"Telegram Bot failed: {loop_e}. Retrying in 10s...")
                time.sleep(10)

    except Exception as e:
        logger.error(f"Telegram Bot initialization failed: {e}")

def main():
    # Fast Exit for Init
    if len(sys.argv) > 1 and sys.argv[1].lower() == "init":
        from .core.setup_wizard import SetupWizard
        SetupWizard().run()
        return

    # Fast Exit for Ralph Build Loop
    if len(sys.argv) > 1 and sys.argv[1].lower() == "build":
        target_dir = sys.argv[2] if len(sys.argv) > 2 else "."
        print_banner()
        print_info(f"Initializing TESS Ralph Builder in {target_dir}")
        
        # We need a headless brain and coding engine to run Ralph
        try:
            user_profile = UserProfile()
            profiles = ProfileManager()
            brain = profiles.get_brain("terminal_user")
            brain.personality = user_profile.personality
            
            coding_engine = CodingEngine(brain)
            ralph = RalphOrchestrator(coding_engine)
            ralph.run_loop(target_dir)
            
        except Exception as e:
            print_error(f"Ralph Build Loop crashed: {e}")
            logger.error(e, exc_info=True)
        return

    # Fast Exit for Coding Mode: tess code [path]
    if len(sys.argv) > 1 and sys.argv[1].lower() == "code":
        target_dir = sys.argv[2] if len(sys.argv) > 2 else "."
        print_banner()
        print_info("Launching TESS Coding Mode...")
        try:
            user_profile = UserProfile()
            profiles = ProfileManager()
            brain = profiles.get_brain("terminal_user")
            brain.personality = user_profile.personality
            
            agent = CodingAgent(brain, workspace_path=target_dir)
            agent.start()
        except Exception as e:
            print_error(f"Coding Mode crashed: {e}")
            logger.error(e, exc_info=True)
        return

    print_banner()

    # Core Initialization
    try:
        user_profile = UserProfile()
        knowledge_db = KnowledgeBase() if Config.is_module_enabled("memory") else None
        profiles = ProfileManager(knowledge_db=knowledge_db)
        executor = Executor(safe_mode=Config.SAFE_MODE)
        security = SecurityEngine(level=Config.get_security_level())
        
        brain = profiles.get_brain("terminal_user")
        brain.personality = user_profile.personality
        brain.history[0]["content"] = Config.get_system_prompt(user_profile.personality)
    except Exception as e:
        print_error(f"Core initialization failed: {e}")
        sys.exit(1)

    # Component Registration
    comps = {
        'brain': brain,
        'executor': executor,
        'security': security,
        'launcher': AppLauncher(),
        'sys_ctrl': SystemController(),
        'file_mgr': FileManager(),
        'task_registry': TaskRegistry(),
        'sysadmin': SysAdminSkill(),
        'command_indexer': CommandIndexer(knowledge_db),
        'knowledge_db': knowledge_db,
        'user_profile': user_profile
    }

    # Conditional Features
    if Config.is_module_enabled("web_search"):
        web_browser = WebBrowser()
        comps['web_search'] = web_browser
        comps['researcher'] = Researcher(brain, knowledge_db, web_browser)
    
    if Config.is_module_enabled("coding"):
        comps['coding_engine'] = CodingEngine(brain)
        comps['coding_agent'] = CodingAgent(brain)

    if Config.is_module_enabled("planner"):
        comps['planner'] = Planner(brain)

    if Config.is_module_enabled("whatsapp"):
        vc = VoiceClient(model_size="base")
        comps['whatsapp'] = WhatsAppClient(brain, voice_client=vc)
        comps['voice_client'] = vc

    if Config.is_module_enabled("media"): 
        comps['youtube_client'] = YouTubeClient(headless=False)

    if Config.is_module_enabled("file_organizer"):
        comps['organizer'] = Organizer(brain)

    if Config.is_module_enabled("gmail") or Config.is_module_enabled("calendar"):
        comps['google_client'] = GoogleClient()

    # Skills (Legacy & Plugins)
    comps['pdf_skill'] = PDFSkill(brain)
    comps['presentation_skill'] = PresentationSkill(brain)
    comps['director'] = ProjectDirector(brain)
    
    # Dynamic Plugin Loader
    from .core.skill_loader import SkillLoader
    skill_loader = SkillLoader(brain)
    skill_registry = skill_loader.load_skills()
    comps['skill_registry'] = skill_registry
    
    # Add loaded skills to comps for access if needed (optional)
    # comps.update(skill_loader.skills)

    # Missing Skills Added
    from .skills.trip_planner import TripPlannerSkill
    from .skills.converter import FileConverter
    from .core.skill_manager import SkillManager

    if Config.is_module_enabled("trip_planner"):
        comps['trip_planner'] = TripPlannerSkill(brain)
    
    if Config.is_module_enabled("file_converter"):
        comps['converter'] = FileConverter()

    if Config.is_module_enabled("skills"): # Legacy Skill Manager
        # Use user name or default
        uid = user_profile.name or "default"
        comps['skill_manager'] = SkillManager(user_id=uid)

    # Local Design Skills
    from .skills.design_genius import DesignGenius
    comps['design_genius'] = DesignGenius(brain)

    # Background Services
    if Config._data.get("integrations", {}).get("librarian", {}).get("enabled", False):
        path = Config._data["integrations"]["librarian"].get("watch_path", os.getcwd())
        Librarian(knowledge_db, watch_path=path).start()
        print_info("Librarian active.")

    TessScheduler(brain=brain).start()

    if Config.TELEGRAM_BOT_TOKEN:
        print_info("Starting Telegram Bot...")
        # Get Screencast from loader if available
        screencast_skill = skill_loader.skills.get('Screencast')
        threading.Thread(target=start_telegram_bot, args=(profiles, comps, screencast_skill), daemon=True).start()

    # Experimental
    if Config.is_module_enabled("privacy_aura"):
        comps['guardian'] = Guardian(comps['sys_ctrl'])
        
    if Config.is_module_enabled("digital_twin"):
        comps['sandbox'] = Sandbox(brain)

    # Boot Sequence
    boot_sequence(comps, Config._data)
    print_provider_info(Config.LLM_PROVIDER, Config.LLM_MODEL)
    print_ready()

    # Main Loop
    while True:
        try:
            user_input = console.input(get_prompt()).strip()
            if not user_input: continue
            
            # System Commands
            if user_input.lower() in ["exit", "quit"]:
                user_profile.save()
                break
                
            if user_input.lower() == "help":
                print_help()
                continue

            if user_input.lower() == "status":
                boot_sequence(comps, Config._data)
                continue

            # Persona
            if user_input.lower().startswith("persona "):
                target = user_input[8:].strip().lower()
                if target in Config.PERSONALITY_PROMPTS:
                    brain.personality = target
                    brain.history[0]["content"] = Config.get_system_prompt(target)
                    print_success(f"Persona: {target.upper()}")
                continue

            # Director Mode
            if user_input.lower().startswith("director:"):
                comps['director'].loop(user_input[9:].strip())
                continue

            # Coding Mode
            if user_input.lower().startswith("code"):
                agent = comps.get('coding_agent')
                if agent:
                    path = user_input[4:].strip() or os.getcwd()
                    agent.start(path)
                else:
                    print_warning("Coding module not enabled. Run 'tess init' to configure.")
                continue

            # Agent Loop
            from .core.agent_loop import AgenticLoop
            AgenticLoop(brain, comps).run(user_input)
            
            user_profile.track_command("agent_task")

        except KeyboardInterrupt:
            break
        except Exception as e:
            print_error(f"Error: {e}")
            logger.error(e, exc_info=True)

    print_goodbye(user_profile.name)

if __name__ == "__main__":
    main()
