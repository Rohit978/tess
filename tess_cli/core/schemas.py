from pydantic import BaseModel, Field
from typing import Optional, Literal, Union

# Shortcuts for readability ;)
L = Literal

class BaseAction(BaseModel):
    """Common fields for all actions."""
    thought: Optional[str] = Field(None, description="Internal monologue")
    reason: Optional[str] = None
    is_dangerous: bool = False

# --- Core Apps ---
class LaunchAppAction(BaseAction):
    action: L["launch_app"]
    app_name: str

class ExecuteCommandAction(BaseAction):
    action: L["execute_command"]
    command: str

class BrowserControlAction(BaseAction):
    action: L["browser_control"]
    sub_action: L["new_tab", "close_tab", "next_tab", "prev_tab", "go_to_url"]
    url: Optional[str] = None

class SystemControlAction(BaseAction):
    action: L["system_control"]
    sub_action: L["volume_up", "volume_down", "mute", "play_pause", "media_next", 
                  "media_prev", "screenshot", "list_processes", "lock", "sleep", 
                  "shutdown", "restart", "type", "press"]
    text: Optional[str] = None # For type
    key: Optional[str] = None  # For press

# --- File & Memory ---
class FileOpAction(BaseAction):
    action: L["file_op"]
    sub_action: L["read", "write", "list", "patch"]
    path: str
    content: Optional[str] = None
    search_text: Optional[str] = None # For patch
    replace_text: Optional[str] = None

class KnowledgeOpAction(BaseAction):
    action: L["knowledge_op"]
    sub_action: L["learn", "search", "status"]
    path: Optional[str] = None
    query: Optional[str] = None

class MemoryAction(BaseAction):
    action: L["memory_op"]
    sub_action: L["remember", "recall", "forget"]
    content: Optional[str] = None
    query: Optional[str] = None
   
# --- Communication ---
class WhatsAppAction(BaseAction):
    action: L["whatsapp_op"]
    sub_action: L["monitor", "send", "stop", "answer", "call"]
    contact: Optional[str] = None
    message: Optional[str] = None

class InstagramAction(BaseAction):
    action: L["instagram_op"]
    sub_action: L["authenticate", "monitor", "send", "read"]
    username: Optional[str] = None
    message: Optional[str] = None

class GmailAction(BaseAction):
    action: L["gmail_op"]
    sub_action: L["list", "send"]
    max_results: int = 5
    to_email: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None

class ReplyAction(BaseAction):
    action: L["reply_op"]
    content: str

# --- Media & Web ---
class YouTubeAction(BaseAction):
    action: L["youtube_op"]
    sub_action: L["play", "search", "pause", "next", "prev", "stop", "mute", "vol_up", "vol_down", "fullscreen"]
    query: Optional[str] = None

class WebSearchAction(BaseAction):
    action: L["web_search_op"]
    query: str

class WebOpAction(BaseAction):
    action: L["web_op"]
    sub_action: L["scrape", "screenshot"]
    url: str

class CalendarAction(BaseAction):
    action: L["calendar_op"]
    sub_action: L["list", "create", "delete"]
    summary: Optional[str] = None
    start_time: Optional[str] = None
    duration_minutes: int = 60

# --- Advanced Skills ---
class TaskOpAction(BaseAction):
    action: L["task_op"]
    sub_action: L["list", "stop"]
    task_id: Optional[str] = None

class PlannerAction(BaseAction):
    action: L["planner_op"]
    goal: str

class OrganizeOpAction(BaseAction):
    action: L["organize_op"]
    path: str
    criteria: str

class CoderAction(BaseAction):
    action: L["code_op"]
    sub_action: L["scaffold", "write", "execute", "test", "fix", "analyze", "outline", "replace_block", "ls", "review", "debug", "ralph_build"]
    filename: Optional[str] = None
    path: Optional[str] = None
    content: Optional[str] = None
    project_type: Optional[L["python", "web", "node"]] = None
    error_log: Optional[str] = None
    goal: Optional[str] = None
    pattern: Optional[str] = None
    search: Optional[str] = None
    replace: Optional[str] = None

class TeachSkillAction(BaseAction):
    action: L["teach_skill"]
    name: str 
    goal: str

class RunSkillAction(BaseAction):
    action: L["run_skill"]
    name: str

class PentestAction(BaseAction):
    action: L["pentest_op"]
    sub_action: L["scan"]
    target: str

class RAGAction(BaseAction):
    action: L["rag_op"]
    sub_action: L["index", "query"]
    path: Optional[str] = None
    query: Optional[str] = None

class TripPlannerAction(BaseAction):
    action: L["trip_planner_op"]
    destination: str
    dates: str
    origin: str = "Current Location"
    budget: Optional[str] = None
    transport_mode: str = "Any"
    preferences: Optional[str] = None

class ResearchAction(BaseAction):
    action: L["research_op"]
    topic: str
    depth: int = 3

class ConverterAction(BaseAction):
    action: L["converter_op"]
    sub_action: L["images_to_pdf", "image_to_pdf", "docx_to_pdf"]
    source_paths: Union[str, list[str]]
    output_filename: Optional[str] = None

class SysAdminAction(BaseAction):
    action: L["sysadmin_op"]
    sub_action: L["wifi_on", "wifi_off", "bluetooth_on", "bluetooth_off", "battery_status", "system_info", "mute_mic", "unmute_mic"]

class PDFOpAction(BaseAction):
    action: L["pdf_op"]
    sub_action: L["merge", "split", "extract_text", "replace_text", "create"]
    source: Optional[Union[str, list[str]]] = None
    output_name: Optional[str] = None
    pages: Optional[str] = None
    search: Optional[str] = None
    replace: Optional[str] = None
    content: Optional[str] = None

class PresentationOpAction(BaseAction):
    action: L["presentation_op"]
    topic: str
    count: int = 5
    style: L["modern", "classic", "tech", "minimal", "gaia", "uncover"] = "modern"
    format: L["pptx", "md"] = "pptx"
    output_name: Optional[str] = None

class BroadcastAction(BaseAction):
    action: L["broadcast_op"]
    sub_action: L["start", "stop"]

class DesignAction(BaseAction):
    action: L["design_op"]
    sub_action: L["create_post", "create_quote"]
    topic: str
    style: L["modern", "minimal", "bold", "neon"] = "modern"

class CodingModeAction(BaseAction):
    action: L["coding_mode_op"]
    sub_action: L["enter"] = "enter"
    path: Optional[str] = None  # Optional workspace path

class ErrorAction(BaseAction):
    action: L["error"]


# Master Union
TessAction = Union[
    LaunchAppAction, ExecuteCommandAction, BrowserControlAction, SystemControlAction,
    FileOpAction, KnowledgeOpAction, WhatsAppAction, InstagramAction, YouTubeAction, TaskOpAction,
    PlannerAction, OrganizeOpAction, WebSearchAction, WebOpAction, ErrorAction, # Error fallback
    CalendarAction, CoderAction, GmailAction, MemoryAction, ReplyAction,
    TeachSkillAction, RunSkillAction, TripPlannerAction, ResearchAction,
    ConverterAction, SysAdminAction, PDFOpAction, PresentationOpAction, 
    BroadcastAction, DesignAction, PentestAction, RAGAction, CodingModeAction
]
