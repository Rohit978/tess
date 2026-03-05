from playwright.sync_api import sync_playwright
import os
import time
import queue
import threading
from .logger import setup_logger
from .terminal_ui import C

logger = setup_logger("WhatsAppClient")

class WhatsAppClient:
    def __init__(self, brain, voice_client=None):
        self.brain = brain
        self.voice_client = voice_client
        self.user_data_dir = os.path.join(os.getcwd(), "data", "whatsapp_session")
        os.makedirs(self.user_data_dir, exist_ok=True)
        self.screenshot_dir = os.path.join(os.getcwd(), "screenshots")
        os.makedirs(self.screenshot_dir, exist_ok=True)
        self.msg_queue = queue.Queue() # Queue for main thread to talk to browser thread
        self.active_contact = None
        self.stop_event = threading.Event()
        self.monitor_thread = None

    def monitor_chat(self, contact_name, mission=None):
        """Starts the WhatsApp monitor in a background thread."""
    def monitor_chat(self, contact_name, mission=None):
        """Starts the WhatsApp monitor in a background thread."""
        # If no contact provided, we still launch to show the dashboard
        if not contact_name:
            logger.info("monitor_chat called with no contact name. Launching dashboard.")
            # We continue instead of returning, treating contact_name as None


        if self.monitor_thread and self.monitor_thread.is_alive():
            logger.debug(f"Monitor already running. Switching focus to {contact_name}")
            self.active_contact = contact_name
            return

        self.stop_event.clear()
        self.monitor_thread = threading.Thread(
            target=self.monitor_loop, 
            args=(self.stop_event, contact_name, mission),
            daemon=True
        )
        self.monitor_thread.start()
        logger.debug(f"WhatsApp Monitor thread started for {contact_name}")
        
        # Wait up to 10 seconds for Playwright loop to bootstrap to prevent GC kills
        for _ in range(20):
            if hasattr(self, 'page') and getattr(self, 'page', None) is not None and not self.page.is_closed():
                break
            time.sleep(0.5)

    def stop(self):
        """Stops the monitor loop."""
        self.stop_event.set()
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.debug("WhatsApp Monitor Stopped.")

        
    def send_message(self, contact, message):
        """Queue a message for a specific contact and ensure monitor is running."""
        if not contact:
             return "Error: No contact specified."
        
        logger.debug(f"Queuing for {contact}: {message}")
        self.msg_queue.put({"contact": contact, "message": message, "action": "send"})
        
        # Auto-start monitor if not running
        if not self.monitor_thread or not self.monitor_thread.is_alive():
            print(f"  {C.DIM}🌐 Launching WhatsApp Monitor...{C.R}")
            self.monitor_chat(contact)
            
            # Wait for it to actually start (hacky but effective)
            for _ in range(10):
                if self.monitor_thread and self.monitor_thread.is_alive():
                    return f"WhatsApp launching... Message queued for {contact}."
                time.sleep(0.5)
            
            return "Error: WhatsApp thread failed to start."
        
        return f"Message queued for {contact}."

    def monitor_loop(self, stop_event, contact_name, mission=None):
        """
        Runs the WhatsApp monitor.
        Accepts a 'mission' to keep conversation focused.
        """
        self.active_contact = contact_name
        logger.debug(f"Starting WhatsApp Monitor for: {contact_name} (Mission: {mission})")
        
        with sync_playwright() as p:
            # Launch Persistent Context (Saves Login)
            try:
                # Add microphone and camera permissions for calls
                print(f"  {C.DIM}🌐 Launching WhatsApp Browser...{C.R}")
                
                # Check for existing context/page to prevent double launch
                if hasattr(self, 'page') and self.page and not self.page.is_closed():
                     print(f"  {C.DIM}🌐 WhatsApp Browser already active.{C.R}")
                     return

                browser = p.chromium.launch_persistent_context(
                    user_data_dir=self.user_data_dir,
                    headless=False,
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                    viewport={"width": 1280, "height": 720},
                    args=["--disable-blink-features=AutomationControlled", "--start-maximized", "--no-sandbox"],
                    permissions=["microphone", "camera"]
                )
                
                self.page = browser.pages[0] if browser.pages else browser.new_page()
                page = self.page
                print(f"  {C.DIM}🌐 Navigating to WhatsApp Web...{C.R}")
                page.goto("https://web.whatsapp.com", timeout=60000)
                
                # 1. Wait for Login (Main Page Load)
                print(f"  {C.DIM}🌐 Waiting for WhatsApp login...{C.R}")
                logger.debug("Waiting for WhatsApp to load...")
                
                login_detected = False
                for i in range(45): # 90 seconds total
                    if page.locator('div[contenteditable="true"], div#pane-side').count() > 0:
                        print(f"  {C.GREEN}✅ Logged in successfully!{C.R}")
                        login_detected = True
                        break
                    
                    # Check for QR Code
                    if page.locator('canvas, div[data-ref]').count() > 0:
                        if i % 5 == 0: # Only print every 10s
                            print(f"  {C.YELLOW}⚠️  Login Required: Please scan the QR code in the WhatsApp window.{C.R}")
                    
                    time.sleep(2)
                
                if not login_detected:
                    qr_path = os.path.join(self.screenshot_dir, "whatsapp_qr.png")
                    page.screenshot(path=qr_path)
                    print(f"  {C.RED}❌ Login timeout. Screenshot saved to {qr_path}{C.R}")
                    self.brain.update_history("system", f"WhatsApp login timeout. QR at {qr_path}")
                    return # Exit cleanly if not logged in
                
                # Cleanup: Close annoying banners (like Notifications/Offline)
                try:
                    banners = page.locator('span[data-icon="x"]').all()
                    for b in banners:
                        if b.is_visible():
                            b.click()
                            time.sleep(0.5)
                except:
                    pass
                
                def open_chat(name):
                    if not name:
                        logger.warning("open_chat called with None/Empty name.")
                        return

                    print(f"  {C.DIM}💬 Searching for contact: {name}...{C.R}")
                    # Robust search locator: variety of common WhatsApp selectors
                    search_selectors = [
                        'div[contenteditable="true"][data-tab="3"]',
                        'div[title="Search input textbox"]',
                        'div.selectable-text[data-lexical-editor="true"]',
                        'label div div[contenteditable="true"]'
                    ]
                    
                    search_box = None
                    for sel in search_selectors:
                        try:
                            loc = page.locator(sel).first
                            if loc.count() > 0 and loc.is_visible():
                                search_box = loc
                                print(f"  {C.DIM}🔍 Found search box via: {sel}{C.R}")
                                break
                        except:
                            continue
                    
                    if not search_box:
                        print(f"  {C.YELLOW}⚠️  Could not find specific search box. Falling back to first contenteditable.{C.R}")
                        search_box = page.locator('div[contenteditable="true"]').first
                        
                    print(f"  {C.DIM}💬 Picking search box...{C.R}")
                    search_box.click()
                    time.sleep(0.5)
                    
                    # Clear search more reliably
                    page.keyboard.press("Control+A")
                    page.keyboard.press("Backspace")
                    time.sleep(0.5)
                    
                    print(f"  {C.DIM}💬 Typing name: {name}...{C.R}")
                    page.keyboard.type(name, delay=120)
                    time.sleep(2)
                    
                    # New: Explicitly wait for results and click the first one
                    print(f"  {C.DIM}💬 Waiting for results and selecting chat...{C.R}")
                    try:
                        # Results usually appear in div[role="listitem"] or specific result rows
                        # We look for a row that contains the name text
                        result = page.locator('div#pane-side div[role="row"]').filter(has_text=name).first
                        if result.count() > 0 and result.is_visible():
                            print(f"  {C.DIM}🎯 Found search result for {name}, clicking...{C.R}")
                            result.click()
                        else:
                            print(f"  {C.DIM}💬 No explicit result found for {name}, trying Enter key...{C.R}")
                            page.keyboard.press("Enter")
                    except Exception as e:
                        print(f"  {C.DIM}⚠️  Error during result selection: {e}. Trying Enter...{C.R}")
                        page.keyboard.press("Enter")
                        
                    time.sleep(3) # Wait for conversation to load
                    
                    # Verify if the chat header matches
                    header = page.locator('header span[title]').filter(has_text=name).first
                    if header.count() > 0:
                         print(f"  {C.GREEN}✅ Chat successfully opened: {name}{C.R}")
                    else:
                         print(f"  {C.YELLOW}⚠️  Opened chat header might not match '{name}', please check the browser.{C.R}")
                    
                    # Capture confirmation screenshot
                    chat_snap = os.path.join(self.screenshot_dir, f"whatsapp_{name.replace(' ', '_')}.png")
                    page.screenshot(path=chat_snap)
                    
                    self.active_contact = name

                if contact_name:
                    open_chat(contact_name)
                
                # Initialize state
                last_msg_text = ""
                style_context = ""
                
                # Initial history load for style
                logger.info("Analyzing chat history for style adaptation (reading last 10 msgs)...")
                try:
                    history_rows = page.locator('div[role="row"]').all()
                    recent_rows = history_rows[-10:]
                    
                    chat_log = []
                    
                    for row in recent_rows:
                        # Determine sender
                        is_me = row.locator('.message-out').count() > 0
                        sender = "Me" if is_me else self.active_contact
                        
                        # Extract text
                        text = row.inner_text().split('\n')[0].strip()
                        
                        if text:
                            chat_log.append(f"{sender}: {text}")
                            last_msg_text = text
                            
                    style_context = "\n".join(chat_log)
                    logger.info(f"Style Context Loaded ({len(chat_log)} msgs).")
                        
                except Exception as e:
                    logger.error(f"Failed to load history: {e}")
                    style_context = ""
                
                # 3. Message Loop
                while not stop_event.is_set():
                    try:
                        # A. CHECK QUEUE (Outgoing from User)
                        while not self.msg_queue.empty():
                            item = self.msg_queue.get()
                            target = item.get("contact")
                            action = item.get("action", "send")
                            msg = item.get("message")
                            
                            # Removed Call/Answer Logic
                            if target and target != self.active_contact:
                                open_chat(target)
                            
                            logger.debug(f"Sending queued message: {msg}")
                            
                            # 1. Focus Input Box (Robust Selector)
                            try:
                                # Try robust structural or title selectors first
                                inp = page.locator('div[contenteditable="true"][data-tab="10"], div[title="Type a message"], footer div[contenteditable="true"]').first
                                if not inp.is_visible():
                                     # Fallback to finding the last contenteditable (almost always the chat box)
                                     inp = page.locator('div[contenteditable="true"]').last
                                     
                                inp.click()
                                time.sleep(0.2)
                                
                                # 2. Type with Human-like Delays
                                import random
                                for char in msg:
                                    page.keyboard.type(char)
                                    # Random delay: 30ms to 100ms per keystroke
                                    time.sleep(random.uniform(0.03, 0.1))
                                
                                time.sleep(0.5)
                                page.keyboard.press("Enter")
                                
                                # 3. Fallback: Click Send Button if Enter didn't work
                                time.sleep(0.5)
                                # The send button aria-label often changes, try multiple
                                send_btn = page.locator('button[aria-label="Send"], span[data-icon="send"], button[data-icon="send"]')
                                if send_btn.count() > 0 and send_btn.first.is_visible():
                                    logger.debug("Enter key failed. Clicking Send button.")
                                    send_btn.first.click()
                                    
                            except Exception as e:
                                logger.error(f"Error sending message: {e}")
                            self.brain.update_history("system", f"Sent to {self.active_contact}: {msg}")
                            # Append to our local context context so we "remember" it for next turn
                            style_context += f"\nMe: {msg}"
                            last_msg_text = msg
                            time.sleep(1)

                        # B. CHECK INCOMING
                        rows = page.locator('div[role="row"]').all()
                        
                        if rows:
                            last_row = rows[-1]
                            is_outgoing = last_row.locator('.message-out').count() > 0
                                
                            if not is_outgoing:
                                try:
                                    # Extract text logic
                                    text = last_row.inner_text().split('\n')[0].strip()
                                        
                                    # Only reply if it's NEW
                                    if text and text != last_msg_text:
                                        logger.info(f"New Message from {self.active_contact}: {text}")
                                        last_msg_text = text
                                        
                                        # Send to Brain
                                        self.brain.update_history("user", f"[WhatsApp - {self.active_contact}]: {text}")
                                        
                                        # Generate Reply WITH STYLE
                                        logger.info("Generating reply with Style Adaptation...")
                                        
                                        mission_prompt = f" MISSION: {mission}" if mission else ""
                                        # Dynamic Persona
                                        user_name = "User"
                                        if hasattr(self.brain, 'profile') and self.brain.profile and self.brain.profile.name:
                                            user_name = self.brain.profile.name
                                        
                                        chat_prompt = f"""
                                        You are {user_name}, the owner of this phone. You are texting on WhatsApp.{mission_prompt}
                                        
                                        RECENT HISTORY:
                                        {style_context[-1000:]}
                                        
                                        PARTNER JUST SAID: "{text}"
                                        
                                        YOUR GOAL: Reply naturally as {user_name}. be casual, use slang if appropriate.
                                        CRITICAL:
                                        1. You are NOT an AI. Do NOT call yourself TESS.
                                        2. You are NOT an assistant. Do NOT offer to help or execute commands.
                                        3. If they ask you to do something (like play music), just say you can't right now or ignore it.
                                        4. Keep it short and human-like.
                                        
                                        IMPORTANT: Output ONLY the message text. No JSON, no quotes, no labels.
                                        """
                                        
                                        reply = self.brain.request_completion(
                                            [{"role": "user", "content": chat_prompt}], 
                                            json_mode=False, 
                                            temperature=0.8
                                        )
                                        
                                        if reply:
                                            logger.info(f"Typing reply: {reply}")
                                            page.keyboard.type(reply)
                                            time.sleep(0.5)
                                            page.keyboard.press("Enter")
                                            last_msg_text = reply
                                            style_context += f"\nMe: {reply}"
                                        else:
                                            logger.warning(f"Brain did not return a reply.")
                                except Exception as e:
                                    logger.error(f"Error extracting text: {e}")
                            else:
                               
                                pass
                                    
                        else:
                            # logger.warning("No rows found. DOM might be different.")
                            pass
                            
                        time.sleep(2) # Poll fast enough
                        
                    except Exception as loop_e:
                        logger.error(f"Monitor Loop Error: {loop_e}")
                        
                        # Break on fatal errors (Browser Closed)
                        err_str = str(loop_e).lower()
                        if "target closed" in err_str or "connection closed" in err_str or "browser has been closed" in err_str:
                            logger.error("Wait - browser seems closed! Exiting Monitor.")
                            # Clean up and exit
                            break
                        
                        time.sleep(5)
                        
                logger.info("Stopping WhatsApp Monitor...")
                browser.close()
                
            except Exception as e:
                logger.error(f"WhatsApp Fatal Error: {e}")
                self.brain.update_history("system", f"WhatsApp Monitor failed: {e}")
