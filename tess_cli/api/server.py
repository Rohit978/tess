import asyncio
import base64
import json
import os
import secrets
import tempfile
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
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

try:
    import fitz as pymupdf_fitz  # pymupdf is the installed package
    def _extract_pdf_text(data: bytes) -> str:
        import io
        doc = pymupdf_fitz.open(stream=data, filetype="pdf")
        return "\n".join(page.get_text() for page in doc.pages[:8]).strip()
except ImportError:
    def _extract_pdf_text(data: bytes) -> str:  # type: ignore[misc]
        return ""

app = FastAPI(title="TESS Terminal Pro")

app.add_middleware(
    CORSMiddleware,
    # Restrict to localhost only. If you need remote access, set the
    # PUBLIC_BASE_URL env var and add it explicitly here.
    allow_origins=[
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        os.getenv("PUBLIC_BASE_URL", ""),
    ],
    allow_credentials=False,   # Never combine credentials=True with wildcard origin
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
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

ROOT = Path(__file__).resolve().parents[2]
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"


@dataclass
class SessionState:
    id: str
    created_at: float = field(default_factory=time.time)
    mode: str = "general"
    resume_text: str = ""
    api_key: str = ""
    events: list[dict[str, Any]] = field(default_factory=list)
    subscribers: list[asyncio.Queue] = field(default_factory=list)


sessions: dict[str, SessionState] = {}


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


def _public_base_url() -> str:
    return os.getenv("PUBLIC_BASE_URL", "http://localhost:8000")


def _get_session(session_id: str) -> SessionState:
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


def _fallback_api_key() -> str:
    return Config.get_api_key("gemini") or Config.get_api_key(Config.get_llm_provider()) or ""


async def _publish(session: SessionState, event_type: str, payload: dict[str, Any]) -> None:
    event = {
        "id": secrets.token_hex(8),
        "type": event_type,
        "createdAt": time.time(),
        "payload": payload,
    }
    session.events.append(event)
    session.events = session.events[-200:]

    dead = []
    for q in session.subscribers:
        try:
            q.put_nowait(event)
        except asyncio.QueueFull:
            dead.append(q)

    for q in dead:
        if q in session.subscribers:
            session.subscribers.remove(q)


def _gemini_generate(api_key: str, parts: list[dict[str, Any]], system_prompt: str) -> str:
    if not api_key:
        return ""

    body = {
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {"temperature": 0.4, "topP": 0.9, "maxOutputTokens": 1800},
    }
    req = urllib.request.Request(
        GEMINI_URL.format(model=GEMINI_MODEL, key=api_key),
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise HTTPException(status_code=502, detail=f"Gemini error: {detail}") from exc
    except urllib.error.URLError as exc:
        raise HTTPException(status_code=502, detail=f"Gemini request failed: {exc.reason}") from exc

    chunks = []
    for candidate in data.get("candidates", []):
        for part in candidate.get("content", {}).get("parts", []):
            txt = part.get("text")
            if txt:
                chunks.append(txt)
    return "\n".join(chunks).strip()


def _answer_prompt(mode: str, resume_text: str) -> str:
    return (
        "You are a live-session copilot. Produce detailed, practical answers for the user in real time. "
        "Use sections: direct answer, key points, suggested spoken response, and follow-up. "
        "If this is a coding question, provide runnable code first, then explanation and complexity.\n\n"
        f"Mode: {mode}\n\nResume/profile context:\n{resume_text[:12000]}"
    )


def _screenshot_prompt(mode: str) -> str:
    return (
        "Analyze the screenshot and infer the actionable question. "
        "If coding context is visible, provide complete runnable code and explanation. "
        f"Current mode: {mode}"
    )


def _generate_text_answer(question: str, mode: str, resume_text: str, api_key: str) -> str:
    if api_key:
        ans = _gemini_generate(
            api_key,
            [{"text": f"Live question:\n{question}"}],
            _answer_prompt(mode, resume_text),
        )
        if ans:
            return ans
    fallback_prompt = (
        f"Mode: {mode}\n\nResume context:\n{resume_text[:4000]}\n\n"
        f"Question:\n{question}\n\nProvide a detailed, practical answer."
    )
    return default_brain.request_completion(
        [{"role": "user", "content": fallback_prompt}],
        json_mode=False,
        temperature=0.5,
    ) or "I could not generate an answer for that yet."


def _extract_resume_text(filename: str, data: bytes) -> str:
    suffix = Path(filename or "").suffix.lower()
    if suffix == ".pdf":
        try:
            text = _extract_pdf_text(data)
            if text:
                return text
        except Exception:
            pass
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("latin-1", errors="ignore")


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
            response_text = f"WhatsApp '{sub}' executed for {contact or 'active chat'}."
        elif action_type == "launch_app":
            response_text = f"Launched {action_response.get('app_name')}."
        elif action_type == "execute_command":
            response_text = "PowerShell command executed."

        return {"response": response_text, "action_log": str(action_response), "status": "success"}
    except Exception as e:
        return {"response": f"Error: {str(e)}", "action_log": str(e), "status": "error"}


# ---------- Dual-device session APIs ----------

@app.post("/api/sessions")
async def create_session() -> dict[str, Any]:
    session_id = secrets.token_urlsafe(8)
    sessions[session_id] = SessionState(id=session_id)
    return {"sessionId": session_id, "joinUrl": f"{_public_base_url()}/phone/{session_id}"}


@app.get("/api/sessions/{session_id}")
async def session_info(session_id: str) -> dict[str, Any]:
    session = _get_session(session_id)
    return {
        "sessionId": session.id,
        "joinUrl": f"{_public_base_url()}/phone/{session.id}",
        "mode": session.mode,
        "hasResume": bool(session.resume_text),
        "hasApiKey": bool(session.api_key or _fallback_api_key()),
        "events": session.events[-50:],
    }


@app.post("/api/sessions/{session_id}/config")
async def configure_session(
    session_id: str,
    apiKey: str = Form(""),
    mode: str = Form("general"),
) -> dict[str, Any]:
    session = _get_session(session_id)
    session.api_key = (apiKey or "").strip()
    session.mode = (mode or "general").strip()
    await _publish(session, "status", {"message": "Session configuration updated."})
    return {"ok": True, "mode": session.mode}


@app.post("/api/sessions/{session_id}/resume")
async def upload_resume(session_id: str, file: UploadFile = File(...)) -> dict[str, Any]:
    session = _get_session(session_id)
    data = await file.read()
    session.resume_text = _extract_resume_text(file.filename or "resume.txt", data)
    await _publish(session, "status", {"message": f"Resume loaded: {file.filename}"})
    return {"ok": True, "characters": len(session.resume_text)}


@app.post("/api/sessions/{session_id}/question")
async def submit_question(session_id: str, question: str = Form(...)) -> dict[str, Any]:
    session = _get_session(session_id)
    q = (question or "").strip()
    if not q:
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    api_key = session.api_key or _fallback_api_key()
    await _publish(session, "transcript", {"source": "typed", "text": q})
    answer = _generate_text_answer(q, session.mode, session.resume_text, api_key)
    await _publish(session, "answer", {"question": q, "answer": answer})
    return {"ok": True, "answer": answer}


@app.post("/api/sessions/{session_id}/audio")
async def submit_audio(session_id: str, file: UploadFile = File(...)) -> dict[str, Any]:
    session = _get_session(session_id)
    api_key = session.api_key or _fallback_api_key()
    data = await file.read()
    mime = file.content_type or "audio/webm"
    transcript = ""

    suffix = Path(file.filename or "chunk.webm").suffix or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(data)
        tmp_path = tmp.name

    try:
        transcript = components["voice_client"].transcribe(tmp_path)
    except Exception:
        transcript = ""
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass

    if not transcript and api_key:
        transcript = _gemini_generate(
            api_key,
            [
                {"text": "Transcribe this audio and extract the question or key prompt."},
                {"inline_data": {"mime_type": mime, "data": base64.b64encode(data).decode("ascii")}},
            ],
            "You are an accurate speech-to-text helper.",
        )

    if not transcript:
        transcript = "No clear question detected from the audio chunk."

    await _publish(session, "transcript", {"source": "system_audio", "text": transcript})
    answer = _generate_text_answer(transcript, session.mode, session.resume_text, api_key)
    await _publish(session, "answer", {"question": transcript, "answer": answer})
    return {"ok": True, "transcript": transcript, "answer": answer}


@app.post("/api/sessions/{session_id}/screenshot")
async def submit_screenshot(session_id: str, file: UploadFile = File(...)) -> dict[str, Any]:
    session = _get_session(session_id)
    api_key = session.api_key or _fallback_api_key()
    data = await file.read()
    mime = file.content_type or "image/png"
    await _publish(session, "status", {"message": "Screenshot received for analysis."})

    if api_key:
        answer = _gemini_generate(
            api_key,
            [
                {"text": _screenshot_prompt(session.mode)},
                {"inline_data": {"mime_type": mime, "data": base64.b64encode(data).decode("ascii")}},
            ],
            _answer_prompt(session.mode, session.resume_text),
        )
    else:
        answer = _generate_text_answer(
            "Screenshot analysis request from live session.",
            session.mode,
            session.resume_text,
            "",
        )

    await _publish(session, "answer", {"question": "Screenshot analysis", "answer": answer})
    return {"ok": True, "answer": answer}


@app.post("/api/sessions/{session_id}/screen-request")
async def request_screen(session_id: str) -> dict[str, Any]:
    session = _get_session(session_id)
    await _publish(session, "screen_request", {"message": "Phone requested laptop screen analysis."})
    return {"ok": True}


@app.get("/api/sessions/{session_id}/events")
async def stream_events(session_id: str) -> StreamingResponse:
    session = _get_session(session_id)
    q: asyncio.Queue = asyncio.Queue(maxsize=30)
    session.subscribers.append(q)

    async def generator():
        try:
            for event in session.events[-40:]:
                yield f"data: {json.dumps(event)}\n\n"
            while True:
                try:
                    event = await asyncio.wait_for(q.get(), timeout=15)
                    yield f"data: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            if q in session.subscribers:
                session.subscribers.remove(q)

    return StreamingResponse(generator(), media_type="text/event-stream")

server_event_loop = None
clipboard_monitor = None
visual_timeline = None


@app.on_event("startup")
async def startup_event():
    global server_event_loop, clipboard_monitor, visual_timeline
    server_event_loop = asyncio.get_running_loop()

    # Start Clipboard Sync Monitor
    def on_clipboard_changed(text):
        if server_event_loop:
            async def do_publish():
                for session in list(sessions.values()):
                    await _publish(session, "clipboard", {"text": text})
            asyncio.run_coroutine_threadsafe(do_publish(), server_event_loop)

    try:
        from ..core.clipboard_sync import ClipboardSyncMonitor
        clipboard_monitor = ClipboardSyncMonitor(on_clipboard_changed)
        clipboard_monitor.start()
    except Exception as e:
        print(f"Failed to start Clipboard Monitor: {e}")

    # Start Visual Timeline (every 60 seconds)
    try:
        from ..core.visual_timeline import VisualTimelineTracker
        visual_timeline = VisualTimelineTracker(default_brain, knowledge_db)
        visual_timeline.start()
    except Exception as e:
        print(f"Failed to start Visual Timeline: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    global clipboard_monitor, visual_timeline
    if clipboard_monitor:
        clipboard_monitor.stop()
    if visual_timeline:
        visual_timeline.stop()


class ClipboardRequest(BaseModel):
    text: str


@app.post("/api/sessions/{session_id}/clipboard")
async def receive_clipboard(session_id: str, request: ClipboardRequest) -> dict[str, Any]:
    session = _get_session(session_id)
    text = request.text
    if clipboard_monitor:
        clipboard_monitor.set_clipboard(text)
    await _publish(session, "status", {"message": "Clipboard synced from mobile device."})
    return {"ok": True}


@app.get("/phone/{session_id}", response_class=HTMLResponse)
async def phone_view(session_id: str):
    _ = _get_session(session_id)
    html = f"""<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>TESS Phone Feed</title>
<style>
body{{font-family:Segoe UI,Arial,sans-serif;margin:0;padding:14px;background:#0f1115;color:#e8ecf1}}
.card{{background:#161b22;border:1px solid #2a313c;border-radius:10px;padding:12px;margin-bottom:10px}}
button{{background:#2f81f7;color:white;border:0;border-radius:8px;padding:10px 12px;font-weight:600}}
.ans{{white-space:pre-wrap;line-height:1.35}}
.muted{{color:#9aa4b2;font-size:12px}}
</style></head>
<body>
<div class="card"><b>TESS Live Feed</b><div class="muted">Session: {session_id}</div></div>
<div class="card"><button id="reqScreen" style="width:100%;">Request laptop screen analysis</button></div>
<div class="card">
  <b>Clipboard Sync</b>
  <div id="pcClipboard" class="muted" style="background:#24292f; padding:8px; border-radius:6px; margin: 8px 0; word-break:break-all;">(no clipboard text)</div>
  <textarea id="phoneClipboard" style="width:100%; box-sizing:border-box; background:#24292f; color:white; border:1px solid #30363d; border-radius:6px; padding:8px; margin-bottom:8px;" placeholder="Type text to send to PC clipboard..."></textarea>
  <button id="sendClipboard" style="width:100%;">Send to PC Clipboard</button>
</div>
<div id="feed"></div>
<script>
const sid = {json.dumps(session_id)};
const feed = document.getElementById("feed");
function add(title, text){{
  const c = document.createElement("div");
  c.className = "card";
  c.innerHTML = "<div class='muted'>" + title + "</div><div class='ans'></div>";
  c.querySelector(".ans").textContent = text || "";
  feed.prepend(c);
}}
document.getElementById("reqScreen").onclick = async () => {{
  await fetch(`/api/sessions/${{sid}}/screen-request`, {{method:"POST"}});
}};
document.getElementById("sendClipboard").onclick = async () => {{
  const txt = document.getElementById("phoneClipboard").value;
  await fetch(`/api/sessions/${{sid}}/clipboard`, {{
    method: "POST",
    headers: {{ "Content-Type": "application/json" }},
    body: JSON.stringify({{ text: txt }})
  }});
}};
const es = new EventSource(`/api/sessions/${{sid}}/events`);
es.onmessage = (m) => {{
  const ev = JSON.parse(m.data);
  if(ev.type === "answer") add("Answer", ev.payload?.answer || "");
  else if(ev.type === "transcript") add("Heard", ev.payload?.text || "");
  else if(ev.type === "status") add("Status", ev.payload?.message || "");
  else if(ev.type === "clipboard") {{
    document.getElementById("pcClipboard").textContent = ev.payload?.text || "";
  }}
}};
</script></body></html>"""
    return HTMLResponse(content=html)


web_path = os.path.join(os.path.dirname(__file__), "../web")
if os.path.exists(web_path):
    app.mount("/", StaticFiles(directory=web_path, html=True), name="static")


def start_server():
    def open_browser():
        time.sleep(1.5)
        webbrowser.open("http://localhost:8000")

    threading.Thread(target=open_browser, daemon=True).start()
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    start_server()
