"""
Orchestrator for TESS Configurable Edition.
Routes actions to appropriate handlers.
"""

import os
import subprocess
import platform
from pathlib import Path
from typing import Dict, Any, Callable, Optional

# Lazy imports for optional features
DocumentAI = None
WorkflowEngine = None
PreferenceMemory = None

# Core Imports
from .architect import Architect
from .librarian import Librarian
from .command_indexer import CommandIndexer
from .browser_controller import BrowserController
from .google_bot import GoogleBot


def _get_document_ai(brain=None):
    global DocumentAI
    if DocumentAI is None:
        from .document_ai import DocumentAI as DA
        DocumentAI = DA
    return DocumentAI(brain)


def _get_workflow_engine(brain=None, orchestrator=None):
    global WorkflowEngine
    if WorkflowEngine is None:
        from .workflow_engine import WorkflowEngine as WE
        WorkflowEngine = WE
    return WorkflowEngine(brain, orchestrator)


def _get_preference_memory(user_id="default"):
    global PreferenceMemory
    if PreferenceMemory is None:
        from .preference_memory import PreferenceMemory as PM
        PreferenceMemory = PM
    return PreferenceMemory(user_id)


class Executor:
    """Executes shell commands safely."""
    
    def __init__(self, safe_mode: bool = True):
        self.safe_mode = safe_mode
        
    def execute_command(self, command: str, confirm_dangerous: bool = True) -> str:
        """Execute a shell command with optional confirmation."""
        if self.safe_mode and confirm_dangerous:
            response = input(f"Execute: {command}? [y/N]: ")
            if response.lower() != 'y':
                return "Command cancelled by user"
        
        try:
            if platform.system() == "Windows":
                result = subprocess.run(
                    ["powershell", "-Command", command],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
            else:
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
            
            output = result.stdout if result.returncode == 0 else result.stderr
            return output or "Command executed successfully (no output)"
        except subprocess.TimeoutExpired:
            return "Command timed out after 30 seconds"
        except Exception as e:
            return f"Error: {e}"


class SystemController:
    """Controls system functions."""
    
    def set_volume(self, direction: str):
        """Adjust system volume."""
        if platform.system() == "Windows":
            if direction == "up":
                os.system("powershell -c $wsh=New-Object -ComObject WScript.Shell; $wsh.SendKeys([char]175)")
            elif direction == "down":
                os.system("powershell -c $wsh=New-Object -ComObject WScript.Shell; $wsh.SendKeys([char]174)")
            elif direction == "mute":
                os.system("powershell -c $wsh=New-Object -ComObject WScript.Shell; $wsh.SendKeys([char]173)")
    
    def media_control(self, action: str):
        """Control media playback."""
        if platform.system() == "Windows":
            key_map = {
                "play": "[char]179",
                "pause": "[char]179",
                "playpause": "[char]179",
                "next": "[char]176",
                "prev": "[char]177",
                "stop": "[char]178"
            }
            if action in key_map:
                os.system(f"powershell -c $wsh=New-Object -ComObject WScript.Shell; $wsh.SendKeys({key_map[action]})")
    
    def take_screenshot(self, path: Optional[str] = None) -> str:
        """Take a screenshot."""
        try:
            from PIL import ImageGrab
            screenshot = ImageGrab.grab()
            
            if not path:
                path = os.path.join(os.path.expanduser("~"), "Desktop", "tess_screenshot.png")
            
            screenshot.save(path)
            return f"Screenshot saved to {path}"
        except ImportError:
            return "PIL not installed. Run: pip install pillow"
        except Exception as e:
            return f"Screenshot failed: {e}"
    
    def list_processes(self, limit: int = 10) -> str:
        """List running processes."""
        try:
            if platform.system() == "Windows":
                result = subprocess.run(
                    ["powershell", "-Command", f"Get-Process | Select-Object -First {limit} | Format-Table -AutoSize"],
                    capture_output=True,
                    text=True
                )
            else:
                result = subprocess.run(
                    ["ps", "aux"],
                    capture_output=True,
                    text=True
                )
                lines = result.stdout.split('\n')[:limit+1]
                return '\n'.join(lines)
            
            return result.stdout
        except Exception as e:
            return f"Failed to list processes: {e}"

    def lock_system(self) -> str:
        """Lock the workstation."""
        if platform.system() == "Windows":
            os.system("rundll32.exe user32.dll,LockWorkStation")
            return "System Locked"
        return "Lock not supported on this OS"

    def sleep_system(self) -> str:
        """Put system to sleep."""
        if platform.system() == "Windows":
            os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
            return "System Sleeping..."
        return "Sleep not supported"

    def shutdown_system(self, restart: bool = False) -> str:
        """Shutdown or restart system."""
        if platform.system() == "Windows":
            cmd = "shutdown /r /t 0" if restart else "shutdown /s /t 0"
            os.system(cmd)
            return "System Restarting..." if restart else "System Shutting Down..."
        return "Shutdown not supported"


class FileManager:
    """Manages file operations."""
    
    def list_dir(self, path: str) -> str:
        """List directory contents."""
        try:
            items = os.listdir(path)
            result = []
            for item in items[:50]:
                full_path = os.path.join(path, item)
                item_type = "📁" if os.path.isdir(full_path) else "📄"
                result.append(f"{item_type} {item}")
            return '\n'.join(result) if result else "Empty directory"
        except Exception as e:
            return f"Error: {e}"
    
    def read_file(self, path: str, max_chars: int = 5000) -> str:
        """Read file contents."""
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(max_chars)
            return content
        except Exception as e:
            return f"Error reading file: {e}"
    
    def write_file(self, path: str, content: str) -> str:
        """Write content to file."""
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            return f"File written: {path}"
        except Exception as e:
            return f"Error writing file: {e}"
    
    def patch_file(self, path: str, search_text: str, replace_text: str) -> str:
        """Replace text in file."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if search_text not in content:
                return "Search text not found in file"
            
            new_content = content.replace(search_text, replace_text)
            
            with open(path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            return f"File patched: {path}"
        except Exception as e:
            return f"Error patching file: {e}"


class AppLauncher:
    """Launches applications."""
    
    def __init__(self):
        self.app_map = self._build_app_map()
    
    def _build_app_map(self) -> Dict[str, str]:
        """Build map of app names to commands."""
        apps = {
            "chrome": "chrome",
            "firefox": "firefox",
            "edge": "msedge",
            "notepad": "notepad",
            "calculator": "calc",
            "explorer": "explorer",
            "cmd": "cmd",
            "powershell": "powershell",
            "code": "code",
            "spotify": "spotify",
        }
        
        if platform.system() == "Darwin":
            apps = {
                "chrome": "open -a 'Google Chrome'",
                "firefox": "open -a Firefox",
                "safari": "open -a Safari",
                "terminal": "open -a Terminal",
            }
        elif platform.system() == "Linux":
            apps = {
                "chrome": "google-chrome",
                "firefox": "firefox",
                "terminal": "gnome-terminal",
            }
        
        return apps
    
    def get_launch_command(self, app_name: str) -> Optional[str]:
        """Get launch command for an app."""
        app_name = app_name.lower().replace('.exe', '')
        return self.app_map.get(app_name)
    
    def launch(self, app_name: str) -> str:
        """Launch an application."""
        cmd = self.get_launch_command(app_name)
        if not cmd:
            return f"Unknown app: {app_name}"
        
        try:
            if platform.system() == "Windows":
                subprocess.Popen(cmd, shell=True)
            else:
                subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return f"Launched {app_name}"
        except Exception as e:
            return f"Failed to launch {app_name}: {e}"


class Orchestrator:
    """
    Routes actions to appropriate handlers.
    Supports all TESS features.
    """
    
    def __init__(self, config, components: Optional[Dict] = None):
        self.config = config
        self.executor = Executor(config.security.safe_mode)
        self.system = SystemController()
        self.files = FileManager()
        self.apps = AppLauncher()
        
        # Optional components (loaded on demand)
        self.components = components or {}
        
        # Initialize Core Features
        self.browser_ctrl = BrowserController()
        self.components["browser_ctrl"] = self.browser_ctrl
        
        if self.config.features.code_generation:
            self.architect = Architect()
            self.components["architect"] = self.architect
            
        if self.config.features.librarian and "knowledge_db" in self.components:
            self.librarian = Librarian(self.components["knowledge_db"])
            self.librarian.start()
            self.components["librarian"] = self.librarian
            
        if self.config.features.command_indexer and "knowledge_db" in self.components:
            self.indexer = CommandIndexer(self.components["knowledge_db"])
            self.components["command_indexer"] = self.indexer
            
        if self.config.features.gmail or self.config.features.calendar:
            self.google_bot = GoogleBot()
            self.components["google_bot"] = self.google_bot
    
    def process_action(self, action: Dict[str, Any], output_callback=None, brain=None) -> str:
        """
        Process an action dictionary.
        
        Args:
            action: Parsed action from Brain
            output_callback: Optional callback for streaming output
            brain: Brain instance for AI features
            
        Returns:
            Result string
        """
        def output(text: str):
            if output_callback:
                output_callback(text)
            else:
                print(text)
        
        action_type = action.get("action", "error")
        
        # Route to handler
        handlers = {
            # Core
            "launch_app": self._handle_launch_app,
            "execute_command": self._handle_execute_command,
            "system_control": self._handle_system_control,
            "file_op": self._handle_file_op,
            "browser_control": self._handle_browser_control,
            "web_search_op": self._handle_web_search,
            "web_op": self._handle_web_op,
            "web_op": self._handle_web_op,
            "reply_op": self._handle_reply,
            "error": self._handle_error,
            
            # Google Bot
            "google_bot_op": self._handle_google_bot,
            
            # Communication
            "whatsapp_op": self._handle_whatsapp,
            "gmail_op": self._handle_gmail,
            "calendar_op": self._handle_calendar,
            
            # Media
            "youtube_op": self._handle_youtube,
            
            # AI & Planning
            "planner_op": self._handle_planner,
            "teach_skill": self._handle_teach_skill,
            "run_skill": self._handle_run_skill,
            "research_op": self._handle_research,
            "trip_planner_op": self._handle_trip_planner,
            "converter_op": self._handle_converter,
            "code_op": self._handle_code,
            "memory_op": self._handle_memory,
            "organize_op": self._handle_organize,
            "task_op": self._handle_task,
            
            # Document AI
            "document_op": self._handle_document,
            
            # Workflows
            "workflow_op": self._handle_workflow,
            
            # Notion
            "notion_op": self._handle_notion,
            
            # Preferences
            "preference_op": self._handle_preference,
        }
        
        handler = handlers.get(action_type)
        if handler:
            try:
                return handler(action, output, brain)
            except Exception as e:
                error_msg = f"Error in {action_type}: {str(e)}"
                output(f"[ERROR] {error_msg}")
                return error_msg
        else:
            return f"Unhandled action type: {action_type}"
    
    # ===== Core Handlers =====
    
    def _handle_launch_app(self, action, output, brain):
        app_name = action.get("app_name", "")
        output(f"[TESS] Launching {app_name}...")
        result = self.apps.launch(app_name)
        output(f"[TESS] {result}")
        return result
    
    def _handle_execute_command(self, action, output, brain):
        command = action.get("command", "")
        is_dangerous = action.get("is_dangerous", False)
        
        output(f"[TESS] Executing: {command}")
        
        if is_dangerous or self._is_dangerous_command(command):
            if self.config.security.level == "HIGH":
                return "Command blocked by HIGH security level"
            if self.config.security.confirm_dangerous:
                confirm = input("⚠️  Dangerous command. Execute? [y/N]: ")
                if confirm.lower() != 'y':
                    return "Command cancelled"
        
        result = self.executor.execute_command(command, confirm_dangerous=False)
        output(f"[OUTPUT]\n{result[:1000]}")
        return result
    
    def _handle_system_control(self, action, output, brain):
        sub = action.get("sub_action", "")
        
        if "volume" in sub:
            self.system.set_volume(sub.replace("volume_", ""))
            return f"Volume {sub}"
        elif "media" in sub or sub in ["play_pause", "play", "pause", "next", "prev"]:
            action_name = sub.replace("media_", "").replace("play_pause", "playpause")
            self.system.media_control(action_name)
            return f"Media {action_name}"
        elif sub == "screenshot":
            result = self.system.take_screenshot()
            output(f"[TESS] {result}")
            return result
            result = self.system.list_processes()
            output(f"[PROCESSES]\n{result}")
            return result
        elif sub == "lock":
            return self.system.lock_system()
        elif sub == "sleep":
            return self.system.sleep_system()
        elif sub == "shutdown":
            return self.system.shutdown_system(restart=False)
        elif sub == "restart":
            return self.system.shutdown_system(restart=True)
        return f"Unknown system action: {sub}"
    
    def _handle_file_op(self, action, output, brain):
        sub = action.get("sub_action", "")
        path = os.path.expanduser(action.get("path", ""))
        
        # Check if path exists
        if not os.path.exists(path):
            return f"Path not found: {path}"
        
        # Handle directories vs files
        is_directory = os.path.isdir(path)
        
        if sub == "list":
            result = self.files.list_dir(path)
            output(f"[FILES]\n{result}")
        elif sub == "read":
            if is_directory:
                # For directories, show contents instead of error
                result = self.files.list_dir(path)
                output(f"[DIRECTORY: {path}]\n{result}")
            else:
                result = self.files.read_file(path)
                output(f"[CONTENT]\n{result[:1000]}...")
        elif sub == "analyze":
            # New: analyze files in directory or single file
            if is_directory:
                from .document_ai import DocumentAI
                doc_ai = DocumentAI(brain)
                results = doc_ai.batch_process(path)
                output(f"[ANALYZED {len(results)} files in {path}]")
                for name, content in list(results.items())[:5]:
                    output(f"  {name}: {content[:100]}...")
                result = f"Analyzed {len(results)} files"
            else:
                # Single file analysis
                from .document_ai import DocumentAI
                doc_ai = DocumentAI(brain)
                result = doc_ai.summarize_document(path)
                output(f"[ANALYSIS]\n{result}")
        elif sub == "write":
            if is_directory:
                result = "Cannot write to a directory"
            else:
                result = self.files.write_file(path, action.get("content", ""))
            output(f"[TESS] {result}")
        elif sub == "patch":
            if is_directory:
                result = "Cannot patch a directory"
            else:
                result = self.files.patch_file(path, action.get("search_text", ""), action.get("replace_text", ""))
            output(f"[TESS] {result}")
        else:
            result = f"Unknown file action: {sub}"
        return result
    
    def _handle_browser_control(self, action, output, brain):
        sub = action.get("sub_action", "")
        
        if not hasattr(self, 'browser_ctrl'):
            return "Browser Controller not initialized"
        
        ctrl = self.browser_ctrl
        
        if sub == "new_tab":
            url = action.get("url")
            return ctrl.new_tab(url)
        elif sub == "close_tab":
            return ctrl.close_tab()
        elif sub == "next_tab":
            return ctrl.next_tab()
        elif sub == "prev_tab":
            return ctrl.prev_tab()
        elif sub == "go_to_url":
            return ctrl.go_to_url(action.get("url"))
        
        return f"Unknown browser action: {sub}"
    
    def _handle_web_search(self, action, output, brain):
        query = action.get("query", "")
        output(f"[TESS] Searching: {query}")
        
        # Try Playwright WebSearch first (better results)
        try:
            from .playwright_browser import WebSearchPlaywright
            searcher = WebSearchPlaywright()
            result = searcher.search_sync(query)
            output(f"[RESULTS]\n{result[:800]}")
            return result
        except Exception as e:
            # Fallback to browser component
            if "web_browser" in self.components and self.config.features.web_search:
                try:
                    result = self.components["web_browser"].search(query)
                    output(f"[RESULTS]\n{result[:800]}")
                    return result
                except Exception as e2:
                    output(f"Search error: {e2}")
        
        # Final fallback: open in browser
        import webbrowser
        import urllib.parse
        webbrowser.open(f"https://www.google.com/search?q={urllib.parse.quote(query)}")
        return f"Opened search in browser"
    
    def _handle_web_op(self, action, output, brain):
        if not self.config.features.web_scraping:
            return "Web scraping disabled in config"
        
        sub = action.get("sub_action", "")
        url = action.get("url", "")
        
        if "web_browser" in self.components:
            browser = self.components["web_browser"]
            if sub == "scrape":
                result = browser.scrape(url)
                output(f"[SCRAPED]\n{result[:800]}")
                return result
            elif sub == "screenshot":
                result = browser.screenshot(url)
                output(f"[TESS] Screenshot: {result}")
                return result
        
        return "Web operations require WebBrowser component"
    
    def _handle_reply(self, action, output, brain):
        content = action.get("content", "")
        output(f"\n🤖 [TESS]: {content}\n")
        return content
    
    def _handle_error(self, action, output, brain):
        reason = action.get("reason", "Unknown error")
        output(f"[ERROR] {reason}")
        return reason
    
    # ===== Document AI Handlers =====
    
    def _handle_document(self, action, output, brain):
        """Handle document analysis and extraction."""
        sub = action.get("sub_action", "")
        path = action.get("path", "")
        
        doc_ai = _get_document_ai(brain)
        
        if sub == "extract_text":
            ext = Path(path).suffix.lower()
            if ext == ".pdf":
                result = doc_ai.extract_text_from_pdf(path)
            elif ext in [".docx", ".doc"]:
                result = doc_ai.extract_text_from_docx(path)
            else:
                result = doc_ai.extract_text_from_image(path)
            output(f"[DOCUMENT]\n{result[:1000]}...")
            return result
        
        elif sub == "summarize":
            result = doc_ai.summarize_document(path)
            output(f"[SUMMARY]\n{result}")
            return result
        
        elif sub == "ocr":
            result = doc_ai.extract_text_from_image(path)
            output(f"[OCR RESULT]\n{result}")
            return result
        
        elif sub == "analyze_image":
            result = doc_ai.analyze_image(path)
            output(f"[IMAGE ANALYSIS]\n{result}")
            return result
        
        return f"Unknown document action: {sub}"
    
    # ===== Workflow Handlers =====
    
    def _handle_workflow(self, action, output, brain):
        """Handle workflow automation."""
        sub = action.get("sub_action", "")
        
        if "workflow_engine" not in self.components:
            self.components["workflow_engine"] = _get_workflow_engine(brain, self)
        
        engine = self.components["workflow_engine"]
        
        if sub == "list":
            result = engine.list_workflows()
            output(f"[WORKFLOWS]\n{result}")
            return result
        
        elif sub == "run":
            name = action.get("name", "")
            result = engine.run_workflow(name, output)
            return result
        
        elif sub == "create_preset":
            preset = action.get("preset", "")
            wf = engine.create_preset_workflow(preset)
            if wf:
                output(f"[TESS] Created workflow: {wf.name}")
                return f"Created workflow: {wf.name}"
            return f"Unknown preset: {preset}"
        
        elif sub == "toggle":
            name = action.get("name", "")
            enabled = engine.toggle_workflow(name)
            status = "enabled" if enabled else "disabled"
            return f"Workflow '{name}' {status}"
        
        return f"Unknown workflow action: {sub}"
    
    # ===== Notion Handlers =====
    
    def _handle_notion(self, action, output, brain):
        """Handle Notion integration."""
        if not getattr(self.config.features, 'notion', False):
            return "Notion disabled. Run 'tess --notion-setup' to configure."
        
        sub = action.get("sub_action", "")
        
        if "notion_client" not in self.components:
            from .notion_client import NotionClient
            self.components["notion_client"] = NotionClient()
        
        client = self.components["notion_client"]
        
        if sub == "search":
            query = action.get("query", "")
            result = client.search(query)
            output(f"[NOTION]\n{result}")
            return result
        
        elif sub == "create_note":
            title = action.get("title", "")
            content = action.get("content", "")
            result = client.create_note(title, content)
            output(f"[TESS] {result}")
            return result
        
        elif sub == "create_page":
            parent = action.get("parent_id", "")
            title = action.get("title", "")
            content = action.get("content", "")
            result = client.create_page(parent, title, content)
            output(f"[TESS] {result}")
            return result
        
        return f"Unknown Notion action: {sub}"
    
    # ===== Preference/Memory Handlers =====
    
    def _handle_preference(self, action, output, brain):
        """Handle user preference learning."""
        sub = action.get("sub_action", "")
        
        if "preference_memory" not in self.components:
            self.components["preference_memory"] = _get_preference_memory()
        
        prefs = self.components["preference_memory"]
        
        if sub == "learn":
            statement = action.get("statement", "")
            result = prefs.learn_from_statement(statement)
            if result:
                output(f"[LEARNED] {result}")
            return result or "Nothing learned"
        
        elif sub == "get":
            category = action.get("category", "")
            key = action.get("key", "")
            value = prefs.get_preference(category, key)
            output(f"[PREFERENCE] {category}.{key}: {value}")
            return str(value)
        
        elif sub == "summary":
            result = prefs.summarize_preferences()
            output(f"[PREFERENCES]\n{result}")
            return result
        
        elif sub == "software":
            sw_type = action.get("type", "")
            pref = prefs.get_software_preference(sw_type)
            output(f"Preferred {sw_type}: {pref}")
            return pref or f"No preference for {sw_type}"
        
        return f"Unknown preference action: {sub}"
    
    # ===== Communication Handlers =====
    
    def _handle_whatsapp(self, action, output, brain):
        if not self.config.features.whatsapp:
            return "WhatsApp disabled in config"
        
        sub = action.get("sub_action", "")
        contact = action.get("contact", "")
        
        if "whatsapp_client" not in self.components:
            # Use Pro-style WhatsApp client with style adaptation and monitor_loop
            from .whatsapp_pro import WhatsAppClient as WhatsAppProClient
            self.components["whatsapp_client"] = WhatsAppProClient(brain)
        
        client = self.components["whatsapp_client"]
        
        # Fallback: If intent is "send" but no message, assume "chat"
        if sub == "send" and not action.get("message"):
            output(f"[WHATSAPP] No message content. Switching to CHAT mode for {contact}...")
            sub = "chat"
        
        if sub == "send":
            msg = action.get("message", "")
            output(f"[WHATSAPP] Sending to {contact}...")
            # Use sync wrapper for async method
            if hasattr(client, 'send_message_sync'):
                result = client.send_message_sync(contact, msg)
            else:
                # Fallback for older clients
                result = client.send_message(contact, msg)
            output(f"[TESS] {result}")
            return result
        elif sub == "monitor" or sub == "chat":
            if "task_registry" not in self.components:
                from .task_registry import TaskRegistry
                self.components["task_registry"] = TaskRegistry()
            task_reg = self.components["task_registry"]
            # Stop existing task for this contact if any?
            # For now just start new one
            task_id = task_reg.start_task(f"WA-{contact}", client.monitor_loop, (contact,))
            return f"Starting chat with {contact} (Task: {task_id})"
        elif sub == "stop":
            return "Use 'task_op' to stop WhatsApp monitors"
        
        return f"Unknown WhatsApp action: {sub}"
    
    def _handle_gmail(self, action, output, brain):
        if not self.config.features.gmail:
            return "Gmail disabled in config"
        
        sub = action.get("sub_action", "")
        
        if "google_client" not in self.components:
            from .google_client import GoogleClient
            self.components["google_client"] = GoogleClient()
        
        client = self.components["google_client"]
        
        if sub == "list":
            result = client.list_emails(action.get("max_results", 5))
            output(f"[GMAIL]\n{result}")
            return result
        elif sub == "send":
            result = client.send_email(
                action.get("to_email", ""),
                action.get("subject", ""),
                action.get("body", "")
            )
            output(f"[TESS] {result}")
            return result
        
        return f"Unknown Gmail action: {sub}"
    
    def _handle_calendar(self, action, output, brain):
        if not self.config.features.calendar:
            return "Calendar disabled in config"
        
        sub = action.get("sub_action", "")
        
        if "google_client" not in self.components:
            from .google_client import GoogleClient
            self.components["google_client"] = GoogleClient()
        
        client = self.components["google_client"]
        
        if sub == "list":
            result = client.list_events()
            output(f"[CALENDAR]\n{result}")
            return result
        elif sub == "create":
            result = client.create_event(
                action.get("summary", ""),
                action.get("start_time", ""),
                action.get("duration_minutes", 60)
            )
            output(f"[TESS] {result}")
            return result
        
        return f"Unknown Calendar action: {sub}"
    
    # ===== Media Handlers =====
    
    def _handle_youtube(self, action, output, brain):
        if not self.config.features.youtube:
            return "YouTube disabled in config"
        
        sub = action.get("sub_action", "")
        
        if "youtube_client" not in self.components:
            # Use Pro-style YouTube client with play_video and control
            from .youtube_pro import YouTubeClient
            self.components["youtube_client"] = YouTubeClient(headless=False)
        
        client = self.components["youtube_client"]
        
        if sub == "play":
            query = action.get("query", "")
            output(f"[YOUTUBE] Playing: {query}")
            result = client.play_video(query)
            output(f"[TESS] {result}")
            return result
        else:
            result = client.control(sub)
            output(f"[TESS] {result}")
            return result
    
    # ===== AI & Skill Handlers =====
    
    def _handle_planner(self, action, output, brain):
        if not self.config.features.planner:
            return "Planner disabled in config"
        
        from .planner import Planner
        planner = Planner(brain)
        
        goal = action.get("goal", "")
        output(f"[PLANNER] Planning: {goal}")
        
        plan = planner.create_plan(goal)
        if plan:
            output(f"[PLAN] {len(plan)} steps")
            planner.execute_plan(plan, self, output)
            return f"Executed plan with {len(plan)} steps"
        return "Planning failed"
    
    def _handle_teach_skill(self, action, output, brain):
        if not self.config.features.skills:
            return "Skills disabled in config"
        
        from .skill_manager import SkillManager
        from .planner import Planner
        
        skill_mgr = SkillManager()
        planner = Planner(brain)
        
        name = action.get("name", "")
        goal = action.get("goal", "")
        
        output(f"[SKILL] Learning '{name}'...")
        plan = skill_mgr.learn_skill(name, goal, planner)
        
        if plan:
            return f"Skill '{name}' learned with {len(plan)} steps"
        return "Failed to learn skill"
    
    def _handle_run_skill(self, action, output, brain):
        if not self.config.features.skills:
            return "Skills disabled in config"
        
        from .skill_manager import SkillManager
        
        skill_mgr = SkillManager()
        name = action.get("name", "")
        
        output(f"[SKILL] Running '{name}'...")
        return skill_mgr.run_skill(name, self, output)
    
    def _handle_research(self, action, output, brain):
        if not self.config.features.research:
            return "Research disabled in config"
        
        from ..skills.research import ResearchSkill
        
        # Ensure web browser - use WebSearchPlaywright for search capability
        if "web_browser" not in self.components:
            try:
                from .playwright_browser import WebSearchPlaywright
                self.components["web_browser"] = WebSearchPlaywright()
            except ImportError:
                # Fallback to Selenium
                from .web_browser import WebBrowser
                self.components["web_browser"] = WebBrowser()
        
        researcher = ResearchSkill(brain, self.components["web_browser"])
        
        topic = action.get("topic", "")
        depth = action.get("depth", 3)
        
        output(f"[RESEARCH] Researching: {topic}")
        result = researcher.run(topic, depth)
        output(f"[TESS] {result}")
        return result
    
    def _handle_trip_planner(self, action, output, brain):
        if not self.config.features.trip_planner:
            return "Trip planner disabled in config"
        
        from ..skills.trip_planner import TripPlannerSkill
        
        if "web_browser" not in self.components:
            from .web_browser import WebBrowser
            self.components["web_browser"] = WebBrowser()
        
        planner = TripPlannerSkill(brain, self.components["web_browser"])
        
        result = planner.run(
            destination=action.get("destination", ""),
            dates=action.get("dates", ""),
            budget=action.get("budget"),
            origin=action.get("origin", "Current Location"),
            transport_mode=action.get("transport_mode", "Any")
        )
        output(f"[TESS] {result}")
        return result
    
    def _handle_converter(self, action, output, brain):
        if not self.config.features.file_converter:
            return "File converter disabled in config"
        
        from ..skills.converter import ConverterSkill
        
        converter = ConverterSkill()
        
        # Handle source paths (could be string or list)
        source_paths = action.get("source_paths", [])
        if isinstance(source_paths, str):
            # Could be comma-separated or single path
            if "," in source_paths:
                source_paths = [p.strip() for p in source_paths.split(",")]
            else:
                source_paths = [source_paths]
        
        # Expand user paths and clean quotes
        cleaned_paths = []
        for path in source_paths:
            path = os.path.expanduser(path.strip('"\''))
            cleaned_paths.append(path)
        
        result = converter.run(
            action.get("sub_action", ""),
            cleaned_paths,
            action.get("output_filename")
        )
        output(f"[CONVERTER] {result}")
        return result
    
    def _handle_code(self, action, output, brain):
        if not self.config.features.code_generation:
            return "Code generation disabled in config"
        
        if not hasattr(self, 'architect'):
            return "Architect component not initialized"
            
        sub = action.get("sub_action", "")
        filename = action.get("filename", "")
        
        if sub == "write":
            content = action.get("content", "")
            return self.architect.write_script(filename, content)
        elif sub == "execute":
            # Run Python script
            return self.architect.execute_script(filename)
        
        return f"Unknown code action: {sub}"
    
    def _handle_memory(self, action, output, brain):
        if not self.config.features.memory:
            return "Memory disabled in config"
        
        sub = action.get("sub_action", "")
        
        from .memory_engine import MemoryEngine
        memory = MemoryEngine()
        
        if sub == "memorize":
            content = action.get("content", "")
            result = memory.memorize(content)
            output(f"[MEMORY] {result}")
            return result
        elif sub == "forget":
            return "Use memory ID to forget specific items"
        
        return f"Unknown memory action: {sub}"
    
    def _handle_organize(self, action, output, brain):
        if not self.config.features.organizer:
            return "Organizer disabled in config"
        
        from .organizer import Organizer
        
        organizer = Organizer(brain)
        path = action.get("path", "")
        criteria = action.get("criteria", "type")
        
        output(f"[ORGANIZER] Organizing {path} by {criteria}...")
        result = organizer.organize(path, criteria)
        output(f"[TESS] {result}")
        return result
    
    def _handle_task(self, action, output, brain):
        if not self.config.features.task_registry:
            return "Task registry disabled in config"
        
        from .task_registry import TaskRegistry
        
        if "task_registry" not in self.components:
            self.components["task_registry"] = TaskRegistry()
        
        registry = self.components["task_registry"]
        sub = action.get("sub_action", "")
        
        if sub == "list":
            result = registry.list_tasks()
            output(f"[TASKS]\n{result}")
            return result
        elif sub == "stop":
            task_id = action.get("task_id", "")
            result = registry.stop_task(task_id)
            output(f"[TESS] {result}")
            return result
        
        return f"Unknown task action: {sub}"
    
    # ===== Helper Methods =====
    
    def _handle_google_bot(self, action, output, brain):
        if not hasattr(self, 'google_bot'):
            return "Google Bot not initialized (check gmail/calendar config)"
        
        bot = self.google_bot
        sub = action.get("sub_action", "")
        
        if sub == "start_session":
            bot.start_session()
            return "Google Session Started"
        elif sub == "stop_session":
            bot.stop_session()
            return "Google Session Stopped"
        elif sub == "get_unread":
            msgs = bot.get_unread_messages()
            output(f"[GMAIL]\n{msgs}")
            return msgs
        elif sub == "send_email":
            to = action.get("to_email")
            subj = action.get("subject")
            body = action.get("body")
            res = bot.send_email(to, subj, body)
            output(f"[GMAIL] {res}")
            return res
        elif sub == "list_events":
            res = bot.list_events()
            output(f"[CALENDAR] {res}")
            return res
        elif sub == "create_event":
            text = action.get("text", "")
            res = bot.create_event(text)
            output(f"[CALENDAR] {res}")
            return res
            
        return f"Unknown Google Bot action: {sub}"

    def _is_dangerous_command(self, command: str) -> bool:
        """Check if command is potentially dangerous."""
        patterns = [
            "rm -rf", "del /s", "format", "rd /s", "rmdir /s",
            "shutdown", "taskkill", "reg delete"
        ]
        cmd_lower = command.lower()
        return any(p in cmd_lower for p in patterns)


def process_action(action, config, output_callback=None, brain=None, components=None) -> str:
    """Convenience function."""
    orch = Orchestrator(config, components or {})
    return orch.process_action(action, output_callback, brain)
