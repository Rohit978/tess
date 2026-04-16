import os
import threading
import webbrowser

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from ..core.app_launcher import AppLauncher
from ..core.architect import Architect
from ..core.brain import Brain
from ..core.browser_controller import BrowserController
from ..core.config import Config
from ..core.executor import Executor
from ..core.file_manager import FileManager
from ..core.google_client import GoogleClient
from ..core.knowledge_base import KnowledgeBase
from ..core.orchestrator import process_action
from ..core.organizer import Organizer
from ..core.planner import Planner
from ..core.profile_manager import ProfileManager
from ..core.security import SecurityEngine
from ..core.system_controller import SystemController
from ..core.task_registry import TaskRegistry
from ..core.voice_client import VoiceClient
from ..core.web_browser import WebBrowser
from ..core.whatsapp_client import WhatsAppClient
from ..core.youtube_client import YouTubeClient

app = FastAPI(title="TESS Terminal Pro")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

knowledge_db = KnowledgeBase()
profiles = ProfileManager(knowledge_db=knowledge_db)
executor = Executor(safe_mode=Config.SAFE_MODE)
security = SecurityEngine(level=Config.get_security_level())
default_brain = Brain(knowledge_db=knowledge_db)

components = {
    "executor": executor,
    "security": security,
    "launcher": AppLauncher(),
    "browser_ctrl": BrowserController(),
    "sys_ctrl": SystemController(),
    "file_mgr": FileManager(),
    "knowledge_db": knowledge_db,
    "task_registry": TaskRegistry(),
    "web_search": WebBrowser(),
    "voice_client": VoiceClient(model_size="base"),
    "whatsapp": WhatsAppClient(default_brain),
    "youtube_client": YouTubeClient(headless=False),
    "organizer": Organizer(default_brain),
    "google_client": GoogleClient(),
    "architect": Architect(),
    "planner": Planner(default_brain),
}


class ConfigRequest(BaseModel):
    llm_provider: str
    groq_api_key: str = None
    openai_api_key: str = None
    deepseek_api_key: str = None
    gemini_api_key: str = None


class ChatRequest(BaseModel):
    message: str
    user_id: str = "web_user"


def _has_key(provider):
    return bool(Config.get_api_key(provider))


def _reload_runtime_components():
    global default_brain
    Config.load()
    executor.safe_mode = Config.SAFE_MODE
    security.set_level(Config.get_security_level())
    default_brain = Brain(knowledge_db=knowledge_db)
    components["whatsapp"] = WhatsAppClient(default_brain)
    components["organizer"] = Organizer(default_brain)
    components["planner"] = Planner(default_brain)


@app.get("/api/config")
async def get_config():
    return {
        "llm_provider": Config.get_llm_provider(),
        "has_groq": _has_key("groq"),
        "has_openai": _has_key("openai"),
        "has_deepseek": _has_key("deepseek"),
        "has_gemini": _has_key("gemini"),
        "security_level": Config.get_security_level(),
    }


@app.post("/api/config")
async def update_config(request: ConfigRequest):
    try:
        provider = (request.llm_provider or "").strip().lower()
        if provider:
            Config._data["llm"]["provider"] = provider

        key_map = {
            "groq": request.groq_api_key,
            "openai": request.openai_api_key,
            "deepseek": request.deepseek_api_key,
            "gemini": request.gemini_api_key,
        }
        for key_provider, key_value in key_map.items():
            if key_value is not None:
                clean_value = key_value.strip()
                Config._data["llm"]["keys"][key_provider] = [clean_value] if clean_value else []

        Config.save()
        _reload_runtime_components()
        return {"status": "success", "message": "Configuration updated and reloaded."}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/api/chat")
async def chat(request: ChatRequest):
    user_input = request.message
    user_id = request.user_id
    print(f"🌐 [WEB] User ({user_id}): {user_input}")

    try:
        brain = profiles.get_brain(user_id)

        # Keep brain-dependent components aligned to this user context.
        components["whatsapp"].brain = brain
        components["organizer"].brain = brain
        components["planner"].brain = brain

        action_response = brain.generate_command(user_input)

        is_safe, reason = security.validate_action(action_response)
        if not is_safe:
            return {
                "response": f"🛡️ SECURITY BLOCK: {reason}",
                "action_log": "Action blocked by Guardian.",
                "status": "blocked",
            }

        process_action(action_response, components, brain)

        action_type = action_response.get("action")
        response_text = "Task executed successfully."

        if action_type == "reply_op":
            response_text = action_response.get("content")
        elif action_type == "error":
            response_text = f"Error: {action_response.get('reason')}"
        elif action_type == "whatsapp_op":
            sub = action_response.get("sub_action")
            contact = action_response.get("contact")
            if sub == "monitor":
                response_text = f"Now monitoring WhatsApp chat with {contact}. I'll alert you to new messages."
            else:
                response_text = f"WhatsApp message sent to {contact}."
        elif action_type == "launch_app":
            response_text = f"Launched {action_response.get('app_name')}."
        elif action_type == "execute_command":
            response_text = "PowerShell command executed."

        return {
            "response": response_text,
            "action_log": str(action_response),
            "status": "success",
        }

    except Exception as e:
        return {
            "response": f"Error: {str(e)}",
            "action_log": str(e),
            "status": "error",
        }


web_path = os.path.join(os.path.dirname(__file__), "../web")
if os.path.exists(web_path):
    app.mount("/", StaticFiles(directory=web_path, html=True), name="static")


def start_server():
    def open_browser():
        import time

        time.sleep(1.5)
        webbrowser.open("http://localhost:8000")

    threading.Thread(target=open_browser, daemon=True).start()
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    start_server()
