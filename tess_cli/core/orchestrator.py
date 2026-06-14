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

        # Guard: Coerce non-string action values (e.g. nested dicts from LLM hallucination)
        if not isinstance(action_type, str):
            logger.warning(f"Non-string action type received: {type(action_type).__name__}. Coercing to reply_op.")
            action_data["action"] = "reply_op"
            action_data.setdefault("content", str(action_type))
            action_type = "reply_op"

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
        content = data.get("content", "").strip()
        if not content:
            return "Empty reply suppressed."
        if self.output_handler:
            try: self.output_handler(content)
            except Exception as e: logger.debug(f"Reply output handler error: {e}")
        print_tess_message(content)
        return f"Replied: {content}"

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

    def _handle_sysadmin_op(self, data):
        sysadmin = self._get_component('sysadmin', "SysAdmin Skill")
        if not sysadmin:
            return
        sub = data.get("sub_action")
        if not sub:
            return out("Error: Missing sysadmin sub_action.", self.output_handler)
        return out(sysadmin.run(sub), self.output_handler)

    def _handle_desktop_vision_op(self, data):
        dv = self.components.get("desktop_vision")
        if not dv:
            from .desktop_vision import DesktopVisionController
            dv = DesktopVisionController()
            self.components["desktop_vision"] = dv

        sub = data.get("sub_action")
        if sub == "list_apps":
            return out(dv.list_visible_apps(query=data.get("query"), limit=data.get("limit", 20)), self.output_handler)
        if sub == "active_app":
            return out(dv.active_app(), self.output_handler)
        if sub == "focus_app":
            target = data.get("title") or data.get("app_name") or data.get("query")
            return out(dv.focus_app(target), self.output_handler)
        if sub == "screenshot":
            return out(dv.screenshot(filename=data.get("filename")), self.output_handler)
        if sub in ("analyze", "look"):
            # 1. Take a fresh screenshot of the entire desktop
            import time as _time
            snap_name = f"vision_{int(_time.time())}.png"
            snap_path_msg = dv.screenshot(filename=snap_name)
            # Resolve the actual file path from the saved message
            snap_path = os.path.join(dv.snapshot_dir, snap_name)
            if not os.path.exists(snap_path):
                return out(f"Analyze Error: screenshot failed — {snap_path_msg}", self.output_handler)
            # 2. Ask the vision LLM to describe/analyze it
            query = data.get("query") or "Describe everything you see on this screen in detail."
            out(f"Analyzing screen with vision model...", self.output_handler)
            analysis = self.brain.request_vision(snap_path, query)
            # 3. Feed result back into conversation history
            self.brain.update_history("user", f"[SCREEN CAPTURE] Query: {query}")
            self.brain.update_history("assistant", f"[VISION RESULT] {analysis}")
            return out(analysis, self.output_handler)
        if sub == "click":
            return out(dv.click(data.get("x"), data.get("y")), self.output_handler)
        if sub == "type":
            return out(dv.type_text(data.get("text")), self.output_handler)
        if sub == "hotkey":
            return out(dv.hotkey(data.get("keys")), self.output_handler)
        if sub == "hide_app":
            target = data.get("title") or data.get("app_name") or data.get("query")
            return out(dv.hide_app(target, pid=data.get("pid")), self.output_handler)
        if sub == "show_app":
            target = data.get("title") or data.get("app_name") or data.get("query")
            return out(dv.show_app(target, pid=data.get("pid")), self.output_handler)
        if sub == "list_hidden_apps":
            return out(dv.list_hidden_apps(), self.output_handler)
        return out(f"Unknown desktop_vision_op sub_action: {sub}", self.output_handler)

    def _handle_dom_op(self, data):
        dom = self.components.get("dom_controller")
        if not dom:
            from .dom_controller import DOMController
            dom = DOMController()
            self.components["dom_controller"] = dom

        sub = data.get("sub_action")
        browser = data.get("browser", "edge")
        headless = bool(data.get("headless", False))
        try:
            if sub == "open":
                return out(
                    dom.open(url=data.get("url"), headless=headless, browser_name=browser),
                    self.output_handler
                )
            if sub == "navigate":
                return out(
                    dom.navigate(data.get("url"), browser_name=browser, headless=headless),
                    self.output_handler
                )
            if sub == "click":
                return out(dom.click(data.get("selector")), self.output_handler)
            if sub == "type":
                return out(dom.type(data.get("selector"), data.get("text"), clear_first=False), self.output_handler)
            if sub == "fill":
                return out(dom.type(data.get("selector"), data.get("text"), clear_first=True), self.output_handler)
            if sub == "press":
                return out(dom.press(data.get("key")), self.output_handler)
            if sub == "wait":
                return out(
                    dom.wait_for(
                        data.get("selector"),
                        state=data.get("state", "visible"),
                        timeout=int(data.get("timeout", 10000)),
                    ),
                    self.output_handler,
                )
            if sub == "text":
                return out(
                    dom.extract_text(selector=data.get("selector"), max_chars=data.get("max_chars", 2000)),
                    self.output_handler
                )
            if sub == "html":
                return out(
                    dom.get_html(selector=data.get("selector"), max_chars=data.get("max_chars", 3000)),
                    self.output_handler
                )
            if sub == "eval":
                return out(dom.evaluate(data.get("script")), self.output_handler)
            if sub == "elements":
                return out(
                    dom.elements(
                        selector=data.get("selector"),
                        limit=int(data.get("limit", 20)),
                    ),
                    self.output_handler,
                )
            if sub == "info":
                return out(dom.info(), self.output_handler)
            if sub == "screenshot":
                return out(dom.screenshot(path=data.get("path")), self.output_handler)
            if sub == "close":
                return out(dom.close(), self.output_handler)
        except Exception as e:
            logger.error(f"DOM operation failed: {e}", exc_info=True)
            return out(f"DOM operation failed: {e}", self.output_handler)

        return out(f"Unknown dom_op sub_action: {sub}", self.output_handler)

    def _handle_hearing_op(self, data):
        vc = self.components.get("voice_client")
        if not vc:
            from .voice_client import VoiceClient
            vc = VoiceClient(model_size="base")
            self.components["voice_client"] = vc

        sub = data.get("sub_action")
        if sub == "listen_ptt":
            duration = int(data.get("duration", 5))
            audio_file = vc.record_audio(duration=max(1, duration))
            if not audio_file:
                return out("No audio captured.", self.output_handler)
            text = vc.transcribe(audio_file)
            return out(f"Heard: {text}" if text else "Heard nothing recognizable.", self.output_handler)
        if sub == "smart_listen":
            audio_file = vc.listen(max_duration=int(data.get("max_duration", 30)))
            if not audio_file:
                return out("No speech detected.", self.output_handler)
            text = vc.transcribe(audio_file)
            return out(f"Heard: {text}" if text else "Heard nothing recognizable.", self.output_handler)
        if sub == "transcribe_file":
            path = data.get("path")
            text = vc.transcribe(path)
            return out(f"Heard: {text}" if text else "Transcription failed.", self.output_handler)
        if sub == "listen_system":
            duration = int(data.get("duration", 6))
            audio_file = vc.record_system_audio(duration=max(1, duration))
            if not audio_file:
                return out("System audio capture failed.", self.output_handler)
            text = vc.transcribe(audio_file)
            return out(f"Heard from system audio: {text}" if text else "No speech detected in system audio.", self.output_handler)
        if sub == "listen_system_reply":
            duration = int(data.get("duration", 6))
            audio_file = vc.record_system_audio(duration=max(1, duration))
            if not audio_file:
                return out("System audio capture failed.", self.output_handler)
            heard = vc.transcribe(audio_file)
            if not heard:
                return out("No speech detected in system audio.", self.output_handler)
            prompt = (
                "You heard this from system audio. Respond briefly and naturally in one or two sentences:\n"
                f"{heard}"
            )
            reply = self.brain.request_completion(
                [{"role": "user", "content": prompt}],
                json_mode=False,
                temperature=0.5
            ) or "I heard that. Could you repeat it once clearly?"
            vc.speak(reply)
            return out(f"Heard: {heard}\nSpoken reply: {reply}", self.output_handler)
        if sub == "speak":
            text = data.get("text")
            ok = vc.speak(text or "")
            return out("Spoken successfully." if ok else "Speak failed.", self.output_handler)
        return out(f"Unknown hearing_op sub_action: {sub}", self.output_handler)

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
            hint = " ".join([
                str(data.get("thought", "")),
                str(data.get("reason", "")),
                str(data.get("content", "")),
                str(data.get("query", "")),
                str(data.get("goal", "")),
            ]).lower()
            if any(k in hint for k in ["answer call", "pick up", "pickup", "accept call"]):
                sub = "answer"
            elif any(k in hint for k in ["call", "voice call", "video call", "ring"]):
                sub = "call"
            else:
                sub = "send" if message else "monitor"

        if sub == "send":
            return out(wa.send_message(contact, message), self.output_handler)
        elif sub in ["monitor", "chat"]:
            wa.monitor_chat(contact if str(contact).lower() != "none" else None)
            return out(f"Monitoring chat...", self.output_handler)
        elif sub == "call":
            return out(wa.call_contact(contact, video=bool(data.get("video", False))), self.output_handler)
        elif sub == "answer":
            return out(wa.answer_call(), self.output_handler)
        elif sub == "stop":
            wa.stop()
            return out("Stopped WhatsApp monitor.", self.output_handler)
             
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
            
            # --- Auto-Review Hook before Commit ---
            if sub == "commit" and "review_op" in self.skill_registry:
                out("\n[TESS REVIEW] Running pre-commit AI code review...", self.output_handler)
                diff_out = exe.execute_command("git diff --cached")
                if not diff_out.strip() or "ERROR:" in diff_out:
                    diff_out = exe.execute_command("git diff")
                
                if diff_out.strip() and "ERROR:" not in diff_out:
                    try:
                        review_result = self.skill_registry["review_op"].execute(
                            {"sub_action": "diff", "content": diff_out}, 
                            {"components": self.components, "output_handler": self.output_handler}
                        )
                        # We just display it and proceed. In a stricter setup, we could block it.
                        out(f"\n[PRE-COMMIT REVIEW FINDINGS]\n{review_result}\n", self.output_handler)
                    except Exception as e:
                        out(f"Auto-review failed: {e}", self.output_handler)
            # ---------------------------------------

            return f"{exe.execute_command(cmds[sub])}"

        return out(f"Unknown git sub_action: {sub}", self.output_handler)
    def _handle_os_op(self, data):
        """
        OS-level UI automation — like dom_op for native Windows apps.
        Uses Windows UI Automation (UIA) via pywinauto with vision fallback.
        """
        # Lazy-init OSController (stored in components for reuse)
        os_ctrl = self.components.get("os_controller")
        if not os_ctrl:
            try:
                from .os_controller import OSController
                os_ctrl = OSController(brain=self.brain)
                self.components["os_controller"] = os_ctrl
            except ImportError as e:
                return out(
                    f"os_op unavailable: pywinauto not installed. Run: pip install pywinauto\n{e}",
                    self.output_handler
                )

        sub    = data.get("sub_action", "")
        query  = data.get("query")
        app    = data.get("app")          # None = active window
        text   = data.get("text")
        ctype  = data.get("control_type")
        path   = data.get("path")
        depth  = int(data.get("max_depth", 4))

        out(f"OS {sub}: {query or path or app or '(active window)'}", self.output_handler)

        if sub == "find":
            if not query:
                return out("os_op(find) requires 'query'.", self.output_handler)
            return out(os_ctrl.find(query, app=app, control_type=ctype), self.output_handler)

        elif sub == "click":
            if not query:
                return out("os_op(click) requires 'query'.", self.output_handler)
            return out(os_ctrl.click(query, app=app, control_type=ctype), self.output_handler)

        elif sub == "type":
            if not query:
                return out("os_op(type) requires 'query' (the field to type into).", self.output_handler)
            if not text:
                return out("os_op(type) requires 'text'.", self.output_handler)
            return out(os_ctrl.type(query, text, app=app), self.output_handler)

        elif sub == "read":
            return out(os_ctrl.read(query=query, app=app), self.output_handler)

        elif sub == "get_tree":
            return out(os_ctrl.get_tree(app=app, max_depth=depth), self.output_handler)

        elif sub == "menu":
            if not path:
                return out("os_op(menu) requires 'path', e.g. 'File->Save As'.", self.output_handler)
            return out(os_ctrl.menu(path, app=app), self.output_handler)

        return out(f"Unknown os_op sub_action: '{sub}'", self.output_handler)

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
        action = str(data.get('action', 'unknown')).lower()
        
        # Match broad conversational indicators in action name
        conv_words = ["conversation", "greet", "talk", "chat", "say", "rapport", "interest", 
                      "clarif", "message", "reply", "respond", "ask", "greeting"]
        
        # Match common conversational payload keys
        conv_keys = {"content", "text", "message", "reply", "response", "query", "msg", "value"}
        
        is_conversational = (
            any(w in action for w in conv_words) or 
            any(k in data for k in conv_keys)
        )
        
        if is_conversational:
            logger.info(f"Re-routing conversational action '{action}' to reply_op to prevent looping warnings.")
            data["action"] = "reply_op"
            if "content" not in data:
                # Find the most conversational parameter available
                for k in ["content", "text", "message", "reply", "response", "query", "msg", "value"]:
                    if k in data:
                        data["content"] = data[k]
                        break
                else:
                    data["content"] = ""
            return self._handle_reply_op(data)

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
