from .schemas import TessAction
from .logger import setup_logger
from .terminal_ui import C, print_tess_message, print_tess_action, print_error, print_warning

logger = setup_logger("Orchestrator")

def process_action(action_data: dict, components: dict, brain):
    """
    Routes the action to the correct component safely.
    Returns the result string for context capture.
    """
    action = action_data.get("action")
    result = ""
    
    # helper for output
    def out(msg):
        print_tess_action(msg)
        logger.info(msg)
        return msg

    # 1. REPLY / CONVERSATION
    if action == "reply_op" or action == "final_reply":
        content = action_data.get("content", "")
        if action == "final_reply":
            from .terminal_ui import console
            from rich.panel import Panel
            console.print(Panel(content, title="✅ TASK COMPLETE", border_style="green"))
        else:
            print_tess_message(content)
        result = f"Sent reply: {content}"

    # 2. SYSTEM CONTROL
    elif action == "system_control":
        sys = components.get('sys_ctrl')
        if not sys: result = out("System Control module is disabled.")
        else:
            sub = action_data.get("sub_action")
            
            # Direct System Actions
            if sub == "shutdown": result = sys.shutdown_system(restart=False)
            elif sub == "restart": result = sys.shutdown_system(restart=True)
            elif sub == "sleep": result = sys.sleep_system()
            elif sub == "lock": result = sys.lock_system()
            elif sub == "list_processes": result = sys.list_processes()
            elif sub == "screenshot": result = sys.take_screenshot()
            
            # Interaction Actions
            elif sub == "type": result = sys.type_text(action_data.get("text"))
            elif sub == "press": result = sys.press_key(action_data.get("key"))
            
            # Audio Actions
            elif sub == "volume_up": result = sys.set_volume("up")
            elif sub == "volume_down": result = sys.set_volume("down")
            elif sub == "mute": result = sys.set_volume("mute")
            
            # Media Actions
            elif sub == "play_pause": result = sys.media_control("playpause")
            elif sub == "media_next": result = sys.media_control("next")
            elif sub == "media_prev": result = sys.media_control("prev")
            elif sub == "media_stop": result = sys.media_control("stop")
            
            else: result = out(f"Unknown system sub-action: {sub}")
            
            if result: out(result)

    # 3. APP LAUNCHER
    elif action == "launch_app":
        if not components.get('launcher'): result = out("App Launcher is disabled.")
        else:
            app_name = action_data.get("app_name")
            res = components['launcher'].launch_app(app_name)
            result = out(res)

    # 4. EXECUTE COMMAND
    elif action == "execute_command":
        exe = components.get('executor')
        if not exe: result = out("Executor is disabled.")
        else:
            cmd = action_data.get("command")
            res = exe.execute_command(cmd)
            out(f"Executed: {cmd}")
            print(f"  {C.DIM}{res}{C.R}")
            result = f"Command Output: {res}"

    # 5. FILE OPERATIONS
    elif action == "file_op":
        fm = components.get('file_mgr')
        if not fm: result = out("File Manager is disabled.")
        else:
            sub = action_data.get("sub_action")
            path = action_data.get("path")
            content = action_data.get("content")
            
            if sub == "read":
                res = fm.read_file(path)
                print(f"\n  {C.BRIGHT_CYAN}━━━ File: {path} ━━━{C.R}")
                print(f"  {C.DIM}{res[:500]}...{C.R}")
                print(f"  {C.BRIGHT_CYAN}{'━' * 40}{C.R}")
                result = f"File Content ({path}): {res}"
            elif sub == "write":
                res = fm.write_file(path, content)
                result = out(res)
            elif sub == "list":
                res = fm.list_dir(path)
                print(f"\n  {C.BRIGHT_CYAN}━━━ Directory: {path} ━━━{C.R}")
                print(f"  {C.DIM}{res}{C.R}")
                result = f"Dir Listing ({path}): {res}"

    # 6. WEB BROWSER (Headless)
    elif action == "web_search_op" or action == "web_op":
        wb = components.get('web_search')
        if not wb: result = out("Web Search is disabled.")
        else:
            if action == "web_search_op":
                query = action_data.get("query")
                res = wb.search_google(query)
                print(f"\n  {C.BRIGHT_GREEN}🔎 Search Results for '{query}':{C.R}")
                print(f"  {C.DIM}{res}{C.R}\n")
                result = f"Search Results: {res}"
            else:
                 url = action_data.get("url")
                 res = wb.scrape_page(url)
                 print(f"\n  {C.BRIGHT_BLUE}📄 Page Content ({url}):{C.R}")
                 print(f"  {C.DIM}{res[:500]}...{C.R}\n")
                 result = f"Page Content: {res}"

    # 7. MEDIA (YouTube)
    elif action == "youtube_op":
        if not components.get('youtube_client'): result = out("YouTube module is disabled.")
        else:
            sub = action_data.get("sub_action")
            if sub == "play":
                out(f"🎵 Playing: {action_data.get('query')}")
                res = components['youtube_client'].play_video(action_data.get("query"))
                result = f"YT Play: {res}"
            else: result = "Unknown YT op"

    # 8. WHATSAPP
    elif action == "whatsapp_op":
        if not components.get('whatsapp'): result = out("WhatsApp module is disabled.")
        else:
            sub = action_data.get("sub_action")
            if sub == "send":
                res = components['whatsapp'].send_message(
                    action_data.get("contact"), 
                    action_data.get("message")
                )
                result = out(res)
            elif sub == "monitor":
                out(f"💬 Monitoring {action_data.get('contact')}...")
                components['whatsapp'].monitor_chat(action_data.get("contact"))
                result = f"Monitoring chat: {action_data.get('contact')}"

    # 9. KNOWLEDGE BASE
    elif action == "knowledge_op":
        result = "Knowledge operations not fully implemented via orchestrator yet."

    # 10. ORGANIZER
    elif action == "organize_op":
        if not components.get('organizer'): result = out("Organizer module is disabled.")
        else:
            path = action_data.get("path")
            res = components['organizer'].organize_directory(path)
            result = out(res)

    # 11. GOOGLE (Gmail/Cal)
    elif action == "gmail_op":
        result = "Gmail operations not fully implemented yet."

    # 12. AUTONOMOUS CODING (The Architect)
    elif action == "code_op":
        engine = components.get('coding_engine')
        if not engine: result = out("Coding Engine is disabled.")
        else:
            sub = action_data.get("sub_action")
            if sub == "scaffold":
                res = engine.scaffold_project(action_data.get("project_type"), action_data.get("path"))
                result = out(res)
            elif sub == "write":
                res = engine.write_file(action_data.get("filename"), action_data.get("content"))
                result = out(res)
            elif sub == "execute":
                res = engine.execute(action_data.get("filename"))
                print(f"\n  {C.BRIGHT_MAGENTA}🚀 Execution Output:{C.R}")
                print(f"  {C.DIM}{res}{C.R}\n")
                result = f"Code Output: {res}"
            elif sub == "test":
                res = engine.test_project(action_data.get("filename"))
                print(f"\n  {C.BRIGHT_YELLOW}🧪 Test Results:{C.R}")
                print(f"  {C.DIM}{res}{C.R}\n")
                result = f"Test Output: {res}"
            elif sub == "fix":
                res = engine.fix_code(action_data.get("filename"), action_data.get("error_log"))
                result = out(res)
            elif sub == "ls":
                res = engine.ls_recursive(action_data.get("path", "."))
                print(f"\n  {C.BRIGHT_BLUE}📂 Directory Tree:{C.R}")
                print(f"{C.WHITE}{res}{C.R}\n")
                result = f"Directory Listing: {res}"
            elif sub == "grep":
                res = engine.grep_search(action_data.get("pattern"), action_data.get("path", "."), action_data.get("exts"))
                print(f"\n  {C.BRIGHT_GREEN}🔍 Grep Results:{C.R}")
                print(f"{C.DIM}{res}{C.R}\n")
                result = f"Grep Results: {res}"
            elif sub == "outline":
                res = engine.get_file_outline(action_data.get("filename"))
                print(f"\n  {C.BRIGHT_CYAN}📜 File Outline ({action_data.get('filename')}):{C.R}")
                print(f"{C.WHITE}{res}{C.R}\n")
                result = f"Outline Result: {res}"
            elif sub == "replace_block":
                res = engine.replace_block(action_data.get("filename"), action_data.get("search"), action_data.get("replace"))
                result = out(res)

    # 13. GIT OPERATIONS
    elif action == "git_op":
        exe = components.get('executor')
        if not exe: result = out("Executor is disabled.")
        else:
            sub = action_data.get("sub_action")
            msg = action_data.get("message", "")
            
            cmd = ""
            if sub == "status": cmd = "git status"
            elif sub == "log": cmd = "git log -n 5 --oneline"
            elif sub == "diff": cmd = "git diff"
            elif sub == "commit": cmd = f'git commit -a -m "{msg}"'
            elif sub == "push": cmd = "git push"
            elif sub == "pull": cmd = "git pull"
            elif sub == "add": cmd = "git add ."
            
            if cmd:
                out(f"Git Action: {sub}")
                res = exe.execute_command(cmd)
                print(f"  {C.DIM}{res}{C.R}")
                result = f"Git {sub}: {res}"
            else:
                result = out(f"Unknown Git sub-action: {sub}")

    # 13. ERROR / UNKNOWN
    elif action == "error":
        result = out(f"AI Error: {action_data.get('reason')}")
    else:
        content = action_data.get("content")
        if content:
            print_tess_message(content)
            result = f"Sent reply: {content}"
        else:
            result = out(f"Unknown Action: {action}")

    # Final History Update for Feedback
    if result:
        brain.update_history("system", result)
    return result

