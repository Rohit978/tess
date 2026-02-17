from .schemas import TessAction
from .logger import setup_logger
from .terminal_ui import C, print_tess_message, print_tess_action, print_error, print_warning

logger = setup_logger("Orchestrator")

def process_action(action_data: dict, components: dict, brain, output_handler=None):
    """
    🎭 The Grand Orchestrator
    
    This function acts as the conductor, routing the Brain's high-level intent 
    to the specific component (Hands) that can convert it into reality.
    """
    action = action_data.get("action")
    result = ""
    
    # helper for output
    def out(msg):
        print_tess_action(msg)
        logger.info(msg)
        if output_handler:
            try:
                output_handler(msg)
            except Exception as e:
                logger.error(f"Output Handler Failed: {e}")
        return msg

    # 1. REPLY / CONVERSATION
    if action == "reply_op" or action == "final_reply":
        content = action_data.get("content", "")
        
        # Send to Output Handler (Telegram/Interface)
        if output_handler:
             try:
                 output_handler(content)
             except: pass

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

    # ─── EXPERIMENTAL (Privacy Aura / Digital Twin) ───
    elif action == "experimental_op":
        sub = action_data.get("sub_action")
        # 🛡️ FUZZY PARAMS
        target = action_data.get("target") or action_data.get("content") or action_data.get("command")

        if sub == "toggle_privacy":
            g = components.get('guardian')
            if not g: result = out("Privacy Aura module is disabled or failed to initialize.")
            else:
                enable = "enable" in str(target).lower() or "on" in str(target).lower()
                result = g.toggle(enable)
                out(result)
        
        elif sub == "simulate":
            s = components.get('sandbox')
            if not s: result = out("Digital Twin sandbox is disabled.")
            elif not target:
                result = out("ERROR: Missing 'target' command for simulation.")
            else:
                sim_res = s.simulate_command(target)
                engine = sim_res.get('engine', 'Unknown Engine')
                safety = sim_res.get('safety_rating', 'UNKNOWN')
                reason = sim_res.get('safety_reason', '')
                raw_out = sim_res.get('output', '')
                explanation = sim_res.get('prediction', '')
                
                display_text = (
                    f"[bold yellow]Command:[/] {target}\n"
                    f"[bold cyan]Engine:[/] {engine}\n"
                    f"[bold {'red' if safety == 'DANGEROUS' else 'green'}]Safety:[/] {safety} ({reason})\n"
                    f"\n[bold magenta]Real Sandbox Output:[/]\n{raw_out}\n\n"
                    f"[bold blue]TESS Interpretation:[/]\n{explanation}"
                )
                
                from rich.panel import Panel
                from .terminal_ui import console
                console.print(Panel(display_text, title="✨ MULTIVERSE SIMULATION ✨", border_style="cyan"))
                result = f"Simulated '{target}' using {engine}. Result: {explanation}"
        else:
            result = out(f"Unknown experimental sub-action: {sub}")

    # 4. EXECUTE COMMAND
    elif action == "execute_command":
        exe = components.get('executor')
        if not exe: result = out("Executor is disabled.")
        else:
            # 🛡️ FUZZY PARAMS: Fallback to common keys if 'command' is missing
            cmd = action_data.get("command") or action_data.get("content") or action_data.get("target")
            
            if not cmd:
                # Last resort: If the AI spoke its mind in the 'thought' but forgot the command, 
                # we might be able to infer it, but for now, we just report the failure.
                result = out("ERROR: Missing 'command' parameter in JSON.")
            else:
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
                # Fallback for content
                actual_content = content or action_data.get("text") or action_data.get("command")
                res = fm.write_file(path, actual_content)
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
                # 🛡️ FUZZY PARAMS
                query = action_data.get("query") or action_data.get("content") or action_data.get("command")
                res = wb.search_google(query)
                print(f"\n  {C.BRIGHT_GREEN}🔎 Search Results for '{query}':{C.R}")
                print(f"  {C.DIM}{res}{C.R}\n")
                result = f"Search Results: {res}"
            else:
                 url = action_data.get("url") or action_data.get("content") # Model often puts URL in content
                 res = wb.scrape_page(url)
                 print(f"\n  {C.BRIGHT_BLUE}📄 Page Content ({url}):{C.R}")
                 print(f"  {C.DIM}{res[:500]}...{C.R}\n")
                 result = f"Page Content: {res}"

    # 7. MEDIA (YouTube)
    # 7. MEDIA (YouTube)
    elif action == "youtube_op":
        client = components.get('youtube_client')
        if not client: 
            print(f"  {C.RED}❌ YouTube component missing.{C.R}")
            result = out("YouTube module is disabled.")
        else:
            query = action_data.get("query") or action_data.get("content")
            sub = action_data.get("sub_action", "play") # Default to play
            
            print(f"  {C.DIM}🎵 YouTube Op: {sub} -> {query}{C.R}")
            
            if sub == "play" or not sub:
                if query:
                    try:
                        res = client.play_video(query)
                        result = f"YT Play: {res}"
                    except Exception as e:
                        print(f"  {C.RED}🔥 YouTube Error: {e}{C.R}")
                        result = f"Error: {e}"
                else:
                    result = "Error: No query provided."
            else: 
                # Handle control actions if implemented, or just error
                result = f"Unknown YT sub_action: {sub}"

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
            elif sub == "monitor" or sub == "chat":
                contact = action_data.get("contact")
                print(f"  {C.DIM}💬 Monitoring {contact}...{C.R}")
                components['whatsapp'].monitor_chat(contact)
                result = f"Monitoring chat: {contact}"

    # 9. KNOWLEDGE BASE
    elif action == "knowledge_op":
        kb = components.get('knowledge_db')
        if not kb: result = out("Knowledge Base is disabled.")
        else:
            sub = action_data.get("sub_action", "search")
            query = action_data.get("query")
            if sub == "search_memory":
                res = kb.search_memory(query)
                result = f"Memory Match: {res}"
            else:
                res = kb.search(query)
                result = f"Docs Match: {res}"
            out(f"Knowledge Search: {query}")

    # 10. ORGANIZER
    elif action == "organize_op":
        if not components.get('organizer'): result = out("Organizer module is disabled.")
        else:
            path = action_data.get("path")
            res = components['organizer'].organize_directory(path)
            result = out(res)

    # 11. PDF OPERATIONS
    elif action == "pdf_op":
        pdf = components.get('pdf_skill')
        if not pdf: result = out("PDF Skill is disabled.")
        else:
            sub = action_data.get("sub_action")
            source = action_data.get("source")
            out_name = action_data.get("output_name")
            
            extras = {
                "pages": action_data.get("pages"),
                "search": action_data.get("search"),
                "replace": action_data.get("replace"),
                "content": action_data.get("content")
            }
            
            res = pdf.run(sub, source, out_name, extras)
            result = out(res)

    # 12. PRESENTATION OPERATIONS
    elif action == "presentation_op":
        pres = components.get('presentation_skill')
        if not pres: result = out("Presentation Skill is disabled.")
        else:
            topic = action_data.get("topic")
            count = action_data.get("count", 5)
            style = action_data.get("style", "modern")
            fmt = action_data.get("format", "pptx")
            out_name = action_data.get("output_name")
            
            out(f"🎨 Designing Presentation: {topic} (Style: {style}, Format: {fmt})")
            res = pres.run("create", topic, count, style, fmt, out_name)
            result = out(res)

    # 11. GOOGLE (Gmail/Cal)
    elif action == "gmail_op" or action == "calendar_op":
        gc = components.get('google_client')
        if not gc: result = out("Google Integrations are disabled.")
        else:
            sub = action_data.get("sub_action")
            if action == "gmail_op":
                if sub == "list": result = gc.list_emails()
                elif sub == "send": result = gc.send_email(action_data.get("to"), action_data.get("subject"), action_data.get("body"))
            else: # calendar_op
                if sub == "list": result = gc.list_events()
                elif sub == "create": result = gc.create_event(action_data.get("summary"), action_data.get("start"))
            
            if result: out(f"Google {action}: {result[:50]}...")

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

    # 14. PLANNER (Multi-step)
    elif action == "planner_op":
        planner = components.get('planner')
        if not planner: result = out("Planner is disabled.")
        else:
            goal = action_data.get("goal")
            out(f"📝 Planning Goal: {goal}")
            plan = planner.create_plan(goal)
            
            if not plan:
                result = out("Failed to generate a valid plan.")
            else:
                print_info(f"Generated {len(plan)} steps. Executing...")
                step_results = []
                for i, step in enumerate(plan):
                    print_info(f"Step {i+1}/{len(plan)}: {step.get('reason', 'Executing...')}")
                    step_res = process_action(step, components, brain)
                    step_results.append(f"Step {i+1} ({step.get('action')}): {step_res}")
                    
                    # 🛡️ SELF-HEALING: Stop and notify if a critical step fails
                    if "ERROR" in step_res.upper() or "[STDERR]" in step_res.upper():
                         out(f"⚠️ Step {i+1} failed. Notifying Brain for recovery...")
                         brain.update_history("system", f"CRITICAL FAILURE in Step {i+1}: {step_res}. Please analyze and propose a fix.")
                         # We stop the sequence and let the brain propose a fix as the next message
                         return f"Stopped execution at step {i+1} due to error: {step_res}"
                
                result = "Plan Execution Summary:\n" + "\n".join(step_results)

    # 15. ERROR / UNKNOWN
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

