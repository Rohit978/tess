import os
import sys
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import threading
import webbrowser

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

from ..core.profile_manager import ProfileManager
from ..core.orchestrator import process_action

# Components
from ..core.executor import Executor
from ..core.config import Config
from ..core.app_launcher import AppLauncher
from ..core.browser_controller import BrowserController
from ..core.system_controller import SystemController
from ..core.file_manager import FileManager
from ..core.knowledge_base import KnowledgeBase
from ..core.planner import Planner
from ..core.web_browser import WebBrowser
from ..core.task_registry import TaskRegistry
from ..core.whatsapp_client import WhatsAppClient
from ..core.youtube_client import YouTubeClient
from ..core.voice_client import VoiceClient
from ..core.organizer import Organizer
from ..core.google_bot import GoogleBot
from ..core.architect import Architect
from ..core.security import SecurityEngine

# Global TESS Instance
app = FastAPI(title="TESS Terminal Pro")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Core Components
knowledge_db = KnowledgeBase()
profiles = ProfileManager(knowledge_db=knowledge_db)
executor = Executor(safe_mode=Config.SAFE_MODE)
security = SecurityEngine(level=Config.SECURITY_LEVEL)
from src.core.brain import Brain
default_brain = Brain(knowledge_db=knowledge_db)

# Global Component Bundle (Shared across users)
components = {
    'executor': executor,
    'security': security,
    'launcher': AppLauncher(),
    'browser_ctrl': BrowserController(),
    'sys_ctrl': SystemController(),
    'file_mgr': FileManager(),
    'knowledge_db': knowledge_db,
    'task_registry': TaskRegistry(),
    'web_browser': WebBrowser(),
    'voice_client': VoiceClient(model_size="base"),
    'whatsapp_client': WhatsAppClient(default_brain), # Brain will be injected per-call but needs default
    'youtube_client': YouTubeClient(headless=False),
    'organizer': Organizer(default_brain),
    'google_bot': GoogleBot(),
    'architect': Architect(),
    'planner': Planner(default_brain)
}

# Request Models
# ... (Existing imports)

class ConfigRequest(BaseModel):
    llm_provider: str
    groq_api_key: str = None
    openai_api_key: str = None
    deepseek_api_key: str = None
    gemini_api_key: str = None

class ChatRequest(BaseModel):
    message: str
    user_id: str = "web_user"

@app.get("/api/config")
async def get_config():
    """Returns current public configuration."""
    return {
        "llm_provider": Config.LLM_PROVIDER,
        # We don't return full keys for security, just masked or simple check
        "has_groq": bool(Config.GROQ_API_KEY),
        "has_openai": bool(Config.OPENAI_API_KEY),
        "has_deepseek": bool(Config.DEEPSEEK_API_KEY),
        "has_gemini": bool(Config.GEMINI_API_KEY),
        "security_level": Config.SECURITY_LEVEL
    }

@app.post("/api/config")
async def update_config(request: ConfigRequest):
    """Updates .env and reloads configuration."""
    try:
        # 1. Read existing .env
        env_path = os.path.join(os.path.dirname(__file__), '../../.env')
        if not os.path.exists(env_path):
             # Try root
             env_path = os.path.join(os.path.dirname(__file__), '../../../.env')
        
        # Simple .env parser/updater
        new_lines = []
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                lines = f.readlines()
        else:
            lines = []

        # Helper to update or append
        config_map = {
            "LLM_PROVIDER": request.llm_provider,
            "GROQ_API_KEY": request.groq_api_key,
            "OPENAI_API_KEY": request.openai_api_key,
            "DEEPSEEK_API_KEY": request.deepseek_api_key,
            "GEMINI_API_KEY": request.gemini_api_key
        }
        
        # Remove None values
        config_map = {k: v for k, v in config_map.items() if v is not None}

        # Update existing lines
        updated_keys = set()
        for line in lines:
            key = line.split("=")[0].strip()
            if key in config_map:
                new_lines.append(f"{key}={config_map[key]}\n")
                updated_keys.add(key)
            else:
                new_lines.append(line)
        
        # Append new keys
        for key, value in config_map.items():
            if key not in updated_keys:
                new_lines.append(f"{key}={value}\n")
        
        # Write back
        with open(env_path, "w") as f:
            f.writelines(new_lines)

        # 2. Reload Config in Memory (Hot Reload)
        # This is tricky because Config is static. We need to manually update it.
        if request.llm_provider: Config.LLM_PROVIDER = request.llm_provider
        if request.groq_api_key: Config.GROQ_API_KEY = request.groq_api_key
        if request.openai_api_key: Config.OPENAI_API_KEY = request.openai_api_key
        if request.deepseek_api_key: Config.DEEPSEEK_API_KEY = request.deepseek_api_key
        if request.gemini_api_key: Config.GEMINI_API_KEY = request.gemini_api_key
        
        # 3. Re-initialize Brain and dependent components
        global brain, components
        brain = Brain(KnowledgeBase()) # Re-init with new config
        components['brain'] = brain
        # Re-init clients that might use the new brain/config
        components['whatsapp_client'] = WhatsAppClient(brain)
        components['organizer'] = Organizer(brain)
        components['planner'] = Planner(brain)
        
        return {"status": "success", "message": "Configuration updated. Brain reloaded."}
        
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/chat")
async def chat(request: ChatRequest):
    user_input = request.message
    user_id = request.user_id
    print(f"🌐 [WEB] User ({user_id}): {user_input}")
    
    try:
        # Get isolated brain for this user
        brain = profiles.get_brain(user_id)
        
        # 1. GENERATE
        action_response = brain.generate_command(user_input)
        
        # 2. SECURITY CHECK
        is_safe, reason = security.validate_action(action_response)
        if not is_safe:
            return {
                "response": f"🛡️ SECURITY BLOCK: {reason}",
                "action_log": "Action blocked by Guardian.",
                "status": "blocked"
            }
            
        # 3. EXECUTE (Full Orchestrator)
        process_action(action_response, components, brain)
        
        # 4. CAPTURE RESPONSE
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
            "status": "success"
        }

    except Exception as e:
        return {
            "response": f"Error: {str(e)}",
            "action_log": str(e),
            "status": "error"
        }

# Serve Static Files (The Frontend)
# We expect src/web to exist
web_path = os.path.join(os.path.dirname(__file__), '../web')
if os.path.exists(web_path):
    app.mount("/", StaticFiles(directory=web_path, html=True), name="static")

def start_server():
    """Launches the API server and opens browser."""
    # Open browser after a slight delay
    def open_browser():
        import time
        time.sleep(1.5)
        webbrowser.open("http://localhost:8000")
        
    threading.Thread(target=open_browser, daemon=True).start()
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    start_server()
