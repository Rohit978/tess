import os
from .schemas import TessAction
from .logger import setup_logger
from .terminal_ui import C, print_tess_message, print_tess_action, print_error, print_warning
from rich.panel import Panel
from .terminal_ui import console

# Setup logging
logger = setup_logger("Orchestrator")

def out(msg, output_handler=None):
    """
    Unified output helper.
    Prints to console, logs to debug, and calls the output_handler if present.
    """
    print_tess_action(msg)
    logger.debug(msg)
    if output_handler:
        try:
            output_handler(msg)
        except Exception as e:
            logger.error(f"Output Callback Error: {e}")
    return msg

class ActionDispatcher:
    """
    Central hub for routing TESS actions to the appropriate components.
    Refactored for dynamic dispatch to avoid boilerplate hell.
    """
    def __init__(self, components, brain, output_handler=None, skill_registry=None):
        self.components = components
        self.brain = brain
        self.output_handler = output_handler
        self.skill_registry = skill_registry or {}

    def dispatch(self, action_data):
        """
        Dynamically routes the action to a handler method.
        Naming convention: _handle_{action_type}
        """
        action_type = action_data.get("action")
        if not action_type:
            return out("Error: No action type specified.", self.output_handler)

        # 1. Check Dynamic Skills First
        if action_type in self.skill_registry:
            skill = self.skill_registry[action_type]
            try:
                # Execute the skill plugin
                # We pass context as full components for now, or just specific needed ones
                context = {"components": self.components} 
                return out(skill.execute(action_data, context), self.output_handler)
            except Exception as e:
                logger.error(f"Skill {skill.name} crashed: {e}", exc_info=True)
                return out(f"Skill Error in {skill.name}: {e}", self.output_handler)

        # 2. Fallback to Hardcoded Handlers
        handler_name = f"_handle_{action_type}"
        handler = getattr(self, handler_name, self._handle_unknown)
        
        # Invoke the handler
        try:
            return handler(action_data)
        except Exception as e:
            logger.error(f"Handler {handler_name} crashed: {e}", exc_info=True)
            return out(f"System Error in {action_type}: {e}", self.output_handler)

    def _get_component(self, name, human_name=None):
        """Helper to safely retrieve components."""
        comp = self.components.get(name)
        if not comp:
            out(f"{human_name or name} is currently disabled.", self.output_handler)
            return None
        return comp

    # --- Core Interaction Handlers ---

    def _handle_reply_op(self, data):
        content = data.get("content", "")
        if self.output_handler:
            try: self.output_handler(content)
            except Exception as e: logger.debug(f"Reply output handler error: {e}")
        print_tess_message(content)
        return f"Replied: {content[:50]}..."

    def _handle_final_reply(self, data):
        content = data.get("content", "")
        if self.output_handler:
            try: self.output_handler(content)
            except Exception as e: logger.debug(f"Final reply output handler error: {e}")
        console.print(Panel(content, title="✅ DONE", border_style="green"))
        return "Task Completed."

    # --- System & App Handlers ---

    def _handle_system_control(self, data):
        sys = self._get_component('sys_ctrl', "System Controller")
        if not sys: return
        
        sub = data.get("sub_action")
        kwargs = {k: v for k, v in data.items() if k not in ["action", "sub_action"]}
        
        # Dynamic mapping for simple no-arg commands
        simple_cmds = {
            "shutdown": (sys.shutdown_system, {"restart": False}),
            "restart": (sys.shutdown_system, {"restart": True}),
            "sleep": (sys.sleep_system, {}),
            "lock": (sys.lock_system, {}),
            "list_processes": (sys.list_processes, {}),
            "screenshot": (sys.take_screenshot, {}),
        }

        if sub in simple_cmds:
            func, args = simple_cmds[sub]
            return func(**args)

        # Complex commands
        if sub == "type": return sys.type_text(data.get("text"))
        if sub == "press": return sys.press_key(data.get("key"))
        if sub in ["volume_up", "volume_down", "mute"]: return sys.set_volume(sub.replace("volume_", ""))
        if sub.startswith("media_") or sub == "play_pause": return sys.media_control(sub.replace("media_", ""))
            
        return out(f"Unknown sys command: {sub}", self.output_handler)

    def _handle_launch_app(self, data):
        # Special case for WhatsApp "launch" which is actually a monitor mode
        raw_app_name = data.get("app_name") or ""
        app_name = str(raw_app_name).lower()
        
        if "whatsapp" in app_name and self.components.get('whatsapp'):
            print(f"  {C.DIM}🌐 Launching WhatsApp Monitor...{C.R}")
            self.components['whatsapp'].monitor_chat(None)
            return "WhatsApp Monitor Launched."

        launcher = self._get_component('launcher', "App Launcher")
        if not launcher: return
        return out(launcher.launch_app(raw_app_name), self.output_handler)

    def _handle_execute_command(self, data):
        exe = self._get_component('executor', "Executor")
        if not exe: return

        cmd = data.get("command") or data.get("content")
        if not cmd: return out("No command provided.", self.output_handler)

        out(f"Executed: {cmd}", self.output_handler)
        res = exe.execute_command(cmd)
        print(f"  {C.DIM}{res}{C.R}")
        return f"Output: {res}"

    # --- Web & Knowledge Handlers ---

    def _handle_web_search_op(self, data):
        wb = self._get_component('web_search', "Web Browser")
        if not wb: return

        query = data.get("query")
        res = wb.search_google(query)
        print(f"\n  {C.BRIGHT_GREEN}🔎 {query}{C.R}")
        print(f"  {C.DIM}{res}{C.R}\n")
        return f"Results: {res}"

    def _handle_web_op(self, data):
        wb = self._get_component('web_search', "Web Browser")
        if not wb: return
        return f"Page Content: {wb.scrape_page(data.get('url'))}"

    def _handle_design_op(self, data):
        dg = self._get_component('design_genius', "DesignGenius")
        if not dg: return
        
        # Direct pass-through
        return out(dg.create_post(data.get("topic"), data.get("style", "modern")), self.output_handler)

    # --- File & Data Handlers ---

    def _handle_file_op(self, data):
        fm = self._get_component('file_mgr', "File Manager")
        if not fm: return

        sub = data.get("sub_action")
        path = data.get("path")
        
        if sub == "read":
            content = fm.read_file(path)
            print(f"\n  {C.BRIGHT_CYAN}📄 {path}{C.R}")
            return f"Content: {content}"
        elif sub == "write":
            return out(fm.write_file(path, data.get("content")), self.output_handler)
        elif sub == "list":
            return f"Files: {fm.list_dir(path)}"
        
        return out(f"Unknown file op: {sub}", self.output_handler)

    def _handle_pdf_op(self, data):
        pdf = self._get_component('pdf_skill', "PDF Skill")
        if pdf: return out(pdf.handle_action(data), self.output_handler)

    def _handle_converter_op(self, data):
        conv = self._get_component('converter', "File Converter")
        if not conv: return

        sub = data.get("sub_action")
        src = data.get("source_paths")
        if sub == "images_to_pdf": return out(conv.images_to_pdf(src, data.get("output_filename")), self.output_handler)
        if sub == "docx_to_pdf": return out(conv.docx_to_pdf(src, data.get("output_filename")), self.output_handler)

    # --- Integration Handlers (Google, WA, Git) ---
    
    def _handle_gmail_op(self, data):
        gc = self._get_component('google_client', "Google Client")
        if not gc: return
        
        if data.get("sub_action") == "send":
            return out(gc.send_email(data.get("to_email"), data.get("subject"), data.get("body")), self.output_handler)
        return out(gc.list_emails(data.get("max_results", 5)), self.output_handler)

    def _handle_calendar_op(self, data):
        gc = self._get_component('google_client', "Google Client")
        if not gc: return
        
        sub = data.get("sub_action")
        if sub == "create":
            return out(gc.create_event(data.get("summary"), data.get("start_time"), data.get("duration_minutes", 60)), self.output_handler)
        return out(gc.list_events(), self.output_handler)

    def _handle_code_op(self, data):
        ce = self._get_component('coding_engine', "Coding Engine")
        if not ce: return
        
        sub = data.get("sub_action")
        # Map sub-actions to CodingEngine methods
        if sub == "scaffold":
            return out(ce.scaffold_project(data.get("project_type"), data.get("path")), self.output_handler)
        elif sub == "write":
            return out(ce.write_file(data.get("filename"), data.get("content")), self.output_handler)
        elif sub == "execute":
            return out(ce.execute(data.get("filename")), self.output_handler)
        elif sub == "test":
            return out(ce.test_project(data.get("filename"), data.get("command")), self.output_handler)
        elif sub == "fix":
            return out(ce.fix_code(data.get("filename"), data.get("error_log")), self.output_handler)
        elif sub == "analyze":
            return out(ce.grep_search(data.get("pattern"), data.get("path", "."), data.get("extensions")), self.output_handler)
        elif sub == "outline":
            return out(ce.get_file_outline(data.get("filename")), self.output_handler)
        elif sub == "replace_block":
            return out(ce.replace_block(data.get("filename"), data.get("search"), data.get("replace")), self.output_handler)
        elif sub == "ls":
            return out(ce.ls_recursive(data.get("path", ".")), self.output_handler)
        elif sub == "review":
            return out(ce.review_code(data.get("filename")), self.output_handler)
        elif sub == "debug":
            return out(ce.debug_code(data.get("filename")), self.output_handler)
        elif sub == "ralph_build":
            from .ralph_loop import RalphOrchestrator
            ralph = RalphOrchestrator(ce)
            target = data.get("path", ".")
            out(f"🚀 Initializing Ralph Builder in {target}...", self.output_handler)
            ralph.run_loop(target)
            return "Ralph Build Loop finished executing."
            
        return out(f"Unknown code op: {sub}", self.output_handler)

    def _handle_whatsapp_op(self, data):
        wa = self._get_component('whatsapp', "WhatsApp")
        if not wa: return

        sub = data.get("sub_action")
        contact = data.get("contact")
        message = data.get("message")
        
        # Fallback if LLM forgets sub_action
        if not sub:
            sub = "send" if message else "monitor"

        if sub == "send":
            return out(wa.send_message(contact, message), self.output_handler)
        elif sub in ["monitor", "chat"]:
            wa.monitor_chat(contact if str(contact).lower() != "none" else None)
            return out(f"Monitoring chat...", self.output_handler)
            
        return out(f"Error: Unknown WhatsApp sub_action '{sub}'", self.output_handler)

    def _handle_youtube_op(self, data):
        yt = self._get_component('youtube_client', "YouTube")
        if not yt: return

        sub = data.get("sub_action")
        query = data.get("query")
        
        # If the LLM forgets sub_action but provides a query, default to play
        if not sub and query:
            q_lower = str(query).lower().strip()
            if q_lower in ["stop", "pause", "quit", "halt", "exit"]:
                sub = "stop" if "stop" in q_lower or "quit" in q_lower or "exit" in q_lower else "pause"
            else:
                sub = "play"
            
        if sub in ["play", "search"]:
             return out(yt.play_video(query), self.output_handler)
             
        # Stop command explicitly closes the browser session
        if sub == "stop":
             msg = yt.stop() or "Stopped YouTube playback."
             return out(msg, self.output_handler)
             
        # Fallback for control commands
        if not sub:
             return out("Error: Missing sub_action (play, pause, etc.)", self.output_handler)
             
        return out(yt.control(sub), self.output_handler)



    def _get_vault(self):
        """Helper to lazy-load VaultManager."""
        if 'vault' not in self.components:
            try:
                from .vault_manager import VaultManager
                self.components['vault'] = VaultManager()
            except ImportError:
                return out("VaultManager not available (cryptography missing?). Install requirements.", self.output_handler)
        return self.components.get('vault')

    def _handle_vault_op(self, data):
        """Handles secure storage operations."""
        vault = self._get_vault()
        if not vault: return
        
        sub = data.get("sub_action")
        key = data.get("key")
        value = data.get("value")
        
        if sub == "store":
            if not key or not value: return out("Provide 'key' and 'value' for store.", self.output_handler)
            return out(vault.store_secret(key, value), self.output_handler)
        
        elif sub == "get":
            if not key: return out("Provide 'key' to retrieve.", self.output_handler)
            secret = vault.get_secret(key)
            if secret: return out(f"SECRET retrieved: {secret}", self.output_handler)
            return out(f"Secret '{key}' not found.", self.output_handler)
        
        elif sub == "list":
            keys = vault.list_secrets()
            return out(f"Vault Secrets: {', '.join(keys) if keys else 'Empty'}", self.output_handler)
        
        elif sub == "delete":
            return out(vault.delete_secret(key), self.output_handler)
            
        return out(f"Unknown vault op: {sub}", self.output_handler)
        
    def _handle_memory_op(self, data):
        """Handles explicit memory operations."""
        kb = self.components.get('knowledge_db')
        if not kb:
            # Try to grab explicit or fallback memory engine if KB is not initialized in components
            # This happens if 'memory' module is disabled but we still want basic memory
            from .memory_engine import MemoryEngine
            # This is a bit hacky, creating a temporary engine if main one isn't there
            # Better to rely on Config.is_module_enabled("memory")
            return out("Memory module is disabled in config.", self.output_handler)

        sub = data.get("sub_action")
        content = data.get("content") or data.get("query")
        
        if sub == "remember":
            if not content: return out("Provide 'content' to remember.", self.output_handler)
            saved = kb.store_memory(content, metadata={"type": "explicit_fact"})
            return out(f"I've remembered: '{content}'", self.output_handler)
            
        elif sub == "recall":
            if not content: return out("Provide 'query' to recall.", self.output_handler)
            results = kb.search_memory(content, n_results=3)
            return out(f"Memory Recall:\n{results}", self.output_handler)
            
        elif sub == "forget":
            return out("Forgetting specific memories is not yet implemented.", self.output_handler)
            
        return out(f"Unknown memory op: {sub}", self.output_handler)

    def _handle_git_op(self, data):
        exe = self._get_component('executor')
        if not exe: return
        
        sub = data.get("sub_action")
        cmds = {
            "status": "git status",
            "log": "git log -n 5 --oneline",
            "diff": "git diff",
            "commit": f'git commit -a -m "{data.get("message", "update")}"',
            "push": "git push",
            "pull": "git pull",
            "add": "git add ."
        }
        
        if sub in cmds:
            out(f"Git: {sub}", self.output_handler)
            return f"{exe.execute_command(cmds[sub])}"

    # --- Skill & Planning Handlers ---

    def _handle_planner_op(self, data):
        planner = self._get_component('planner', "Planner")
        if not planner: return

        plan = planner.create_plan(data.get("goal"))
        if not plan: return out("Plan generation failed.", self.output_handler)

        results = []
        for i, step in enumerate(plan):
            print_tess_action(f"Step {i+1}: {step.get('reason')}")
            res = self.dispatch(step)
            results.append(f"Step {i+1}: {res}")
            if "ERROR" in str(res).upper():
                return f"Plan failed at step {i+1}: {res}"
        return "\n".join(results)

    def _handle_run_skill(self, data):
        sm = self._get_component('skill_manager', "Skill Manager")
        if sm: return out(sm.execute_skill(data.get("name")), self.output_handler)

    def _handle_teach_skill(self, data):
        sm = self._get_component('skill_manager', "Skill Manager")
        if sm: return out(sm.learn_skill(data.get("name"), data.get("goal")), self.output_handler)

    # --- Catch-all ---

    def _handle_coding_mode_op(self, data):
        """Launch the interactive coding agent mode."""
        agent = self._get_component('coding_agent', "Coding Agent")
        if not agent:
            return out("Coding Agent not available. Enable 'coding' module in config.", self.output_handler)
        path = data.get("path") or os.getcwd()
        agent.start(path)
        return "Exited coding mode."

    def _handle_unknown(self, data):
        """Fallback for unhandled actions."""
        action = data.get('action', 'unknown')
        msg = f"I don't know how to handle '{action}' yet."
        out(msg, self.output_handler)
        logger.warning(f"Unhandled action: {action}")
        self.brain.update_history("system", f"Action '{action}' not supported.")
        return msg


def process_action(action_data: dict, components: dict, brain, output_handler=None):
    """
    Main entry point.
    Instantiates the dispatcher and lets it rip.
    """
    # Extract registry from components if present
    registry = components.get("skill_registry", {})
    
    dispatcher = ActionDispatcher(components, brain, output_handler, skill_registry=registry)
    result = dispatcher.dispatch(action_data)
    
    # Log valid system results to brain history
    if result:
        brain.update_history("system", str(result))
    return result
