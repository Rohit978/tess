from pydantic import BaseModel, Field
from typing import Optional, Literal, Union

# Base Action
class BaseAction(BaseModel):
    thought: Optional[str] = Field(None, description="The AI's reasoning process")
    reason: Optional[str] = Field(None, description="Explanation of why this action triggers")
    is_dangerous: bool = Field(False, description="Flag for dangerous operations")

# 1. Launch App
class LaunchAppAction(BaseAction):
    action: Literal["launch_app"]
    app_name: str

# 2. Execute Command
class ExecuteCommandAction(BaseAction):
    action: Literal["execute_command"]
    command: str

# 3. Browser Control
class BrowserControlAction(BaseAction):
    action: Literal["browser_control"]
    sub_action: Literal["new_tab", "close_tab", "next_tab", "prev_tab", "go_to_url"]
    url: Optional[str] = None

# 4. System Control
class SystemControlAction(BaseAction):
    action: Literal["system_control"]
    sub_action: Literal["volume_up", "volume_down", "mute", "play_pause", "media_next", "media_prev", "screenshot", "list_processes", "lock", "sleep", "shutdown", "restart"]

# 5. File Operations
class FileOpAction(BaseAction):
    action: Literal["file_op"]
    sub_action: Literal["read", "write", "list", "patch"]
    path: str
    content: Optional[str] = None
    search_text: Optional[str] = None
    replace_text: Optional[str] = None

# 6. Knowledge Operations
class KnowledgeOpAction(BaseAction):
    action: Literal["knowledge_op"]
    sub_action: Literal["learn", "search", "status"]
    path: Optional[str] = None
    query: Optional[str] = None

# 7. WhatsApp Operations
class WhatsAppAction(BaseAction):
    action: Literal["whatsapp_op"]
    sub_action: Literal["monitor", "send", "stop", "answer", "call"]
    contact: Optional[str] = None
    message: Optional[str] = None

# 8. YouTube Operations
class YouTubeAction(BaseAction):
    action: Literal["youtube_op"]
    sub_action: Literal["play", "pause", "next", "mute", "vol_up", "vol_down", "fullscreen"]
    query: Optional[str] = None

# 9. Task Operations
class TaskOpAction(BaseAction):
    action: Literal["task_op"]
    sub_action: Literal["list", "stop"]
    task_id: Optional[str] = None

# 10. Planner Operations
class PlannerAction(BaseAction):
    action: Literal["planner_op"]
    goal: str

# 11. Organizer Operations
class OrganizeOpAction(BaseAction):
    action: Literal["organize_op"]
    path: str
    criteria: str

# 12. Web Search Operations
class WebSearchAction(BaseAction):
    action: Literal["web_search_op"]
    query: str

# 13. Web Operations (Scrape/Screenshot)
class WebOpAction(BaseAction):
    action: Literal["web_op"]
    sub_action: Literal["scrape", "screenshot"]
    url: str

# 14. Error Action
class ErrorAction(BaseAction):
    action: Literal["error"]

# 15. Calendar Operations
class CalendarAction(BaseAction):
    action: Literal["calendar_op"]
    sub_action: Literal["list", "create", "delete"]
    summary: Optional[str] = None
    start_time: Optional[str] = None
    duration_minutes: Optional[int] = 60
    event_id: Optional[str] = None

# 16. Coder Operations (The Architect)
class CoderAction(BaseAction):
    action: Literal["code_op"]
    sub_action: Literal["scaffold", "write", "execute", "test", "fix", "analyze", "summarize"]
    filename: Optional[str] = None
    path: Optional[str] = None
    content: Optional[str] = None
    project_type: Optional[Literal["python", "web", "node"]] = None
    error_log: Optional[str] = None
    goal: Optional[str] = None

# 17. Gmail Operations
class GmailAction(BaseAction):
    action: Literal["gmail_op"]
    sub_action: Literal["list", "send"]
    max_results: int = 5
    to_email: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None

# 18. Memory Operations (The Librarian)
class MemoryAction(BaseAction):
    action: Literal["memory_op"]
    sub_action: Literal["memorize", "forget"]
    content: str
    
# 19. Conversation/Reply (The Soul)
class ReplyAction(BaseAction):
    action: Literal["reply_op"]
    content: str

# 20. Skill Operations (Learning Mode)
class TeachSkillAction(BaseAction):
    action: Literal["teach_skill"]
    name: str = Field(..., description="Name of the skill (e.g. 'Daily Report')")
    goal: str = Field(..., description="Describe what the skill does (e.g. 'Open email and list inbox')")

class RunSkillAction(BaseAction):
    action: Literal["run_skill"]
    name: str = Field(..., description="Name of the skill to run")

class TripPlannerAction(BaseAction):
    action: Literal["trip_planner_op"]
    destination: str
    dates: str
    origin: Optional[str] = "Current Location"
    budget: Optional[str] = None
    transport_mode: Optional[str] = "Any"
    preferences: Optional[str] = None

# 22. Deep Research Operations
class ResearchAction(BaseAction):
    action: Literal["research_op"]
    topic: str
    depth: Optional[int] = 3

# 23. File Converter Operations
class ConverterAction(BaseAction):
    action: Literal["converter_op"]
    sub_action: Literal["images_to_pdf", "image_to_pdf", "docx_to_pdf"]
    source_paths: Union[str, list[str]] # Can be one file or list of files
    output_filename: Optional[str] = None

# 24. SysAdmin Operations
class SysAdminAction(BaseAction):
    action: Literal["sysadmin_op"]
    sub_action: Literal["wifi_on", "wifi_off", "bluetooth_on", "bluetooth_off", "battery_status", "system_info", "mute_mic", "unmute_mic"]

# 25. PDF Operations
class PDFOpAction(BaseAction):
    action: Literal["pdf_op"]
    sub_action: Literal["merge", "split", "extract_text", "replace_text", "create"]
    source: Optional[Union[str, list[str]]] = None
    output_name: Optional[str] = None
    pages: Optional[str] = None
    search: Optional[str] = None
    replace: Optional[str] = None
    content: Optional[str] = None

# 26. Presentation Operations
class PresentationOpAction(BaseAction):
    action: Literal["presentation_op"]
    topic: str
    count: Optional[int] = 5
    style: Optional[Literal["modern", "classic", "tech", "minimal", "gaia", "uncover"]] = "modern"
    format: Optional[Literal["pptx", "md"]] = "pptx"
    output_name: Optional[str] = None

# 27. Screen Broadcast Operations
class BroadcastAction(BaseAction):
    action: Literal["broadcast_op"]
    sub_action: Literal["start", "stop"]

# Union Type for easy validation
TessAction = Union[
    LaunchAppAction,
    ExecuteCommandAction,
    BrowserControlAction,
    SystemControlAction,
    FileOpAction,
    KnowledgeOpAction,
    WhatsAppAction,
    YouTubeAction,
    TaskOpAction,
    PlannerAction,
    OrganizeOpAction,
    WebSearchAction,
    WebOpAction,
    ErrorAction,
    CalendarAction,
    CoderAction,
    GmailAction,
    MemoryAction,
    ReplyAction,
    TeachSkillAction,
    RunSkillAction,
    TripPlannerAction,
    TripPlannerAction,
    ResearchAction,
    ConverterAction,
    SysAdminAction,
    PDFOpAction,
    PresentationOpAction,
    BroadcastAction
]
