from .schemas import TessAction
from .logger import setup_logger
from .terminal_ui import C, print_tess_message, print_tess_action, print_error, print_warning

logger = setup_logger("Orchestrator")

def process_action(action_data: dict, components: dict, brain):
    """
    Routes the action to the correct component safely.
    Checks if component is enabled (not None).
    """
    action = action_data.get("action")
    
    # helper for output
    def out(msg):
        print_tess_action(msg)
        logger.info(msg)

    # 1. REPLY / CONVERSATION
    if action == "reply_op":
        content = action_data.get("content", "")
        print_tess_message(content)

    # 2. SYSTEM CONTROL
    elif action == "system_control":
        if not components.get('sys_ctrl'): return out("System Control module is disabled.")
        
        sub = action_data.get("sub_action")
        if sub == "shutdown": components['sys_ctrl'].shutdown()
        elif sub == "restart": components['sys_ctrl'].restart()
        elif sub == "sleep": components['sys_ctrl'].sleep()
        elif sub == "lock": components['sys_ctrl'].lock()
        elif sub == "type": components['sys_ctrl'].type_text(action_data.get("text"))
        elif sub == "press": components['sys_ctrl'].press_key(action_data.get("key"))
        elif sub == "screenshot": 
            res = components['sys_ctrl'].take_screenshot()
            out(res)

    # 3. APP LAUNCHER
    elif action == "launch_app":
        if not components.get('launcher'): return out("App Launcher is disabled.")
        
        app_name = action_data.get("app_name")
        res = components['launcher'].launch_app(app_name)
        out(res)

    # 4. EXECUTE COMMAND
    elif action == "execute_command":
        if not components.get('executor'): return out("Executor is disabled.")
        
        cmd = action_data.get("command")
        res = components['executor'].execute(cmd)
        out(f"Executed: {cmd}")
        print(f"  {C.DIM}{res}{C.R}")
        brain.update_history("system", f"Command Output: {res}")

    # 5. FILE OPERATIONS
    elif action == "file_op":
        if not components.get('file_mgr'): return out("File Manager is disabled.")
        
        sub = action_data.get("sub_action")
        path = action_data.get("path")
        content = action_data.get("content")
        
        if sub == "read":
            res = components['file_mgr'].read_file(path)
            print(f"\n  {C.BRIGHT_CYAN}━━━ File: {path} ━━━{C.R}")
            print(f"  {C.DIM}{res[:500]}...{C.R}")
            print(f"  {C.BRIGHT_CYAN}{'━' * 40}{C.R}")
            brain.update_history("system", f"File Content ({path}): {res[:1000]}")
        elif sub == "write":
            res = components['file_mgr'].write_file(path, content)
            out(res)
        elif sub == "list":
            res = components['file_mgr'].list_dir(path)
            print(f"\n  {C.BRIGHT_CYAN}━━━ Directory: {path} ━━━{C.R}")
            print(f"  {C.DIM}{res}{C.R}")
            brain.update_history("system", f"Dir Listing: {res}")

    # 6. WEB BROWSER (Headless)
    elif action == "web_search_op" or action == "web_op":
        if not components.get('web_search'): return out("Web Search is disabled.")
        
        if action == "web_search_op":
            query = action_data.get("query")
            res = components['web_search'].search_google(query)
            print(f"\n  {C.BRIGHT_GREEN}🔎 Search Results for '{query}':{C.R}")
            print(f"  {C.DIM}{res}{C.R}\n")
            brain.update_history("system", f"Search Results: {res}")
        else:
             url = action_data.get("url")
             res = components['web_search'].scrape_page(url)
             print(f"\n  {C.BRIGHT_BLUE}📄 Page Content ({url}):{C.R}")
             print(f"  {C.DIM}{res[:500]}...{C.R}\n")
             brain.update_history("system", f"Page Content: {res[:2000]}")

    # 7. MEDIA (YouTube)
    elif action == "youtube_op":
        if not components.get('youtube_client'): return out("YouTube module is disabled.")
        
        sub = action_data.get("sub_action")
        if sub == "play":
            out(f"🎵 Playing: {action_data.get('query')}")
            res = components['youtube_client'].play_video(action_data.get("query"))
            brain.update_history("system", f"YT Play: {res}")
        else:
            pass

    # 8. WHATSAPP
    elif action == "whatsapp_op":
        if not components.get('whatsapp'): return out("WhatsApp module is disabled.")
        
        sub = action_data.get("sub_action")
        if sub == "send":
            res = components['whatsapp'].send_message(
                action_data.get("contact"), 
                action_data.get("message")
            )
            out(res)
        elif sub == "monitor":
            out(f"💬 Monitoring {action_data.get('contact')}...")
            components['whatsapp'].monitor_chat(action_data.get("contact"))

    # 9. KNOWLEDGE BASE
    elif action == "knowledge_op":
        if not components.get('knowledge_db'): return out("Memory module is disabled.")
        pass

    # 10. ORGANIZER
    elif action == "organize_op":
        if not components.get('organizer'): return out("Organizer module is disabled.")
        
        path = action_data.get("path")
        res = components['organizer'].organize_directory(path)
        out(res)

    # 11. GOOGLE (Gmail/Cal)
    elif action == "gmail_op":
        if not components.get('google_client'): return out("Google Integration is disabled.")
        pass
        pass

    # 12. AUTONOMOUS CODING (The Architect)
    elif action == "code_op":
        engine = components.get('coding_engine')
        if not engine: return out("Coding Engine is disabled.")
        
        sub = action_data.get("sub_action")
        if sub == "scaffold":
            res = engine.scaffold_project(action_data.get("project_type"), action_data.get("path"))
            out(res)
        elif sub == "write":
            res = engine.write_file(action_data.get("filename"), action_data.get("content"))
            out(res)
        elif sub == "execute":
            res = engine.execute(action_data.get("filename"))
            print(f"\n  {C.BRIGHT_MAGENTA}🚀 Execution Output:{C.R}")
            print(f"  {C.DIM}{res}{C.R}\n")
            brain.update_history("system", f"Code Output: {res}")
        elif sub == "test":
            res = engine.test_project(action_data.get("filename"))
            print(f"\n  {C.BRIGHT_YELLOW}🧪 Test Results:{C.R}")
            print(f"  {C.DIM}{res}{C.R}\n")
            brain.update_history("system", f"Test Output: {res}")
        elif sub == "fix":
            res = engine.fix_code(action_data.get("filename"), action_data.get("error_log"))
            out(res)
        elif sub == "analyze" or sub == "summarize":
            res = engine.analyze_workspace(action_data.get("path", "."))
            print(f"\n  {C.BRIGHT_BLUE}📊 Workspace Analysis:{C.R}")
            print(f"  {C.WHITE}{res}{C.R}\n")
            brain.update_history("system", f"Analysis: {res}")


    # 13. ERROR / UNKNOWN
    elif action == "error":

        print_error(f"AI Error: {action_data.get('reason')}")

    else:
        # FALLBACK: If the action has a "content" field, treat it as a reply
        content = action_data.get("content")
        if content:
            print_tess_message(content)
        else:
            print_warning(f"Unknown Action: {action}")

