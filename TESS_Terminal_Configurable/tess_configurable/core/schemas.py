"""
Pydantic schemas for TESS action validation.
Adapted from original TESS for configurable edition.
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal, Union, List


# Base Action
class BaseAction(BaseModel):
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


# 6. WhatsApp Operations
class WhatsAppAction(BaseAction):
    action: Literal["whatsapp_op"]
    sub_action: Literal["chat", "monitor", "send", "stop"]
    contact: Optional[str] = None
    message: Optional[str] = None


# 7. YouTube Operations
class YouTubeAction(BaseAction):
    action: Literal["youtube_op"]
    sub_action: Literal["play", "pause", "next", "mute", "vol_up", "vol_down"]
    query: Optional[str] = None


# 8. Task Operations
class TaskOpAction(BaseAction):
    action: Literal["task_op"]
    sub_action: Literal["list", "stop"]
    task_id: Optional[str] = None


# 9. Web Search
class WebSearchAction(BaseAction):
    action: Literal["web_search_op"]
    query: str


# 10. Web Operations
class WebOpAction(BaseAction):
    action: Literal["web_op"]
    sub_action: Literal["scrape", "screenshot"]
    url: str


# 11. Planner
class PlannerAction(BaseAction):
    action: Literal["planner_op"]
    goal: str


# 12. File Organizer
class OrganizeOpAction(BaseAction):
    action: Literal["organize_op"]
    path: str
    criteria: str


# 13. Calendar
class CalendarAction(BaseAction):
    action: Literal["calendar_op"]
    sub_action: Literal["list", "create"]
    summary: Optional[str] = None
    start_time: Optional[str] = None


# 14. Gmail
class GmailAction(BaseAction):
    action: Literal["gmail_op"]
    sub_action: Literal["list", "send"]
    to_email: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None
    max_results: int = 5


# 15. Code Operations
class CodeAction(BaseAction):
    action: Literal["code_op"]
    sub_action: Literal["write", "execute"]
    filename: str
    content: Optional[str] = None


# 16. Memory
class MemoryAction(BaseAction):
    action: Literal["memory_op"]
    sub_action: Literal["memorize", "forget"]
    content: str


# 17. Reply/Conversation
class ReplyAction(BaseAction):
    action: Literal["reply_op"]
    content: str


# 18. Skills
class TeachSkillAction(BaseAction):
    action: Literal["teach_skill"]
    name: str
    goal: str


class RunSkillAction(BaseAction):
    action: Literal["run_skill"]
    name: str


# 19. Research
class ResearchAction(BaseAction):
    action: Literal["research_op"]
    topic: str
    depth: Optional[int] = 3


# 20. Converter
class ConverterAction(BaseAction):
    action: Literal["converter_op"]
    sub_action: Literal["images_to_pdf", "docx_to_pdf"]
    source_paths: Union[str, list]
    output_filename: Optional[str] = None


# 21. Error
class ErrorAction(BaseAction):
    action: Literal["error"]


# Union Type for validation
TessAction = Union[
    LaunchAppAction,
    ExecuteCommandAction,
    BrowserControlAction,
    SystemControlAction,
    FileOpAction,
    WhatsAppAction,
    YouTubeAction,
    TaskOpAction,
    WebSearchAction,
    WebOpAction,
    PlannerAction,
    OrganizeOpAction,
    CalendarAction,
    GmailAction,
    CodeAction,
    MemoryAction,
    ReplyAction,
    TeachSkillAction,
    RunSkillAction,
    ResearchAction,
    ConverterAction,
    ErrorAction
]
