from .schemas import TessAction
from .logger import setup_logger

logger = setup_logger("Orchestrator")

def process_action(action_data: dict, components: dict, brain):
    """
    Routes the action to the correct component safely.
    Checks if component is enabled (not None).
    """
    action = action_data.get("action")
    
    # helper for output
    def out(msg):
        print(f"[TESS] {msg}")
        logger.info(msg)

    # 1. REPLY / CONVERSATION
    if action == "reply_op":
        content = action_data.get("content", "")
        print(f"\n💬 TESS: {content}\n")
        # brain.update_history("assistant", content) # Already done in Brain

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
        # Security Check should have happened before this
        res = components['executor'].execute(cmd)
        out(f"Executed: {cmd}")
        print(res)
        brain.update_history("system", f"Command Output: {res}")

    # 5. FILE OPERATIONS
    elif action == "file_op":
        if not components.get('file_mgr'): return out("File Manager is disabled.")
        
        sub = action_data.get("sub_action")
        path = action_data.get("path")
        content = action_data.get("content")
        
        if sub == "read":
            res = components['file_mgr'].read_file(path)
            print(f"\n--- File: {path} ---\n{res[:500]}...\n----------------")
            brain.update_history("system", f"File Content ({path}): {res[:1000]}")
        elif sub == "write":
            res = components['file_mgr'].write_file(path, content)
            out(res)
        elif sub == "list":
            res = components['file_mgr'].list_dir(path)
            print(res)
            brain.update_history("system", f"Dir Listing: {res}")

    # 6. WEB BROWSER (Headless)
    elif action == "web_search_op" or action == "web_op":
        if not components.get('web_search'): return out("Web Search is disabled.")
        
        if action == "web_search_op":
            query = action_data.get("query")
            res = components['web_search'].search_google(query)
            print(f"\n🔎 Search Results for '{query}':\n{res}\n")
            brain.update_history("system", f"Search Results: {res}")
        else:
             # Scrape
             url = action_data.get("url")
             res = components['web_search'].scrape_page(url)
             print(f"\n📄 Page Content ({url}):\n{res[:500]}...\n")
             brain.update_history("system", f"Page Content: {res[:2000]}")

    # 7. MEDIA (YouTube)
    elif action == "youtube_op":
        if not components.get('youtube_client'): return out("YouTube module is disabled.")
        
        sub = action_data.get("sub_action")
        if sub == "play":
            out(f"[YOUTUBE] Playing: {action_data.get('query')}")
            res = components['youtube_client'].play_video(action_data.get("query"))
            brain.update_history("system", f"YT Play: {res}")
        else:
            # pause, stop, chrome modes
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
            out(f"Monitoring {action_data.get('contact')}...")
            components['whatsapp'].monitor_chat(action_data.get("contact"))

    # 9. KNOWLEDGE BASE
    elif action == "knowledge_op":
        if not components.get('knowledge_db'): return out("Memory module is disabled.")
        # Usually handled internally by Brain, but explicit actions can go here
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
        # Dispatch to google client
        pass # To be implemented in GoogleClient wrapper

    # 12. ARCHITECT (Coding)
    elif action == "code_op":
        if not components.get('architect'): return out("Architect (Coding) module is disabled.")
        # implementation
        pass

    # 13. ERROR / UNKNOWN
    elif action == "error":
        out(f"AI Error: {action_data.get('reason')}")

    else:
        out(f"Unknown Action: {action}")
