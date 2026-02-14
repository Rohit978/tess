from playwright.sync_api import sync_playwright
import os
import time
import queue
from .logger import setup_logger

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
        
    def send_message(self, contact, message):
        """Queue a message for a specific contact."""
        logger.info(f"Queuing for {contact}: {message}")
        self.msg_queue.put({"contact": contact, "message": message, "action": "send"})

    def monitor_loop(self, stop_event, contact_name, mission=None):
        """
        Runs the WhatsApp monitor.
        Accepts a 'mission' to keep conversation focused.
        """
        self.active_contact = contact_name
        logger.info(f"Starting WhatsApp Monitor for: {contact_name} (Mission: {mission})")
        logger.info(f"Brain Provider: {self.brain.provider.upper()} | Model: {self.brain.model}")
        
        with sync_playwright() as p:
            # Launch Persistent Context (Saves Login)
            try:
                # Add microphone and camera permissions for calls
                # Reverting to Windows Chrome but we will use specific selectors to find the Call dropdown
                # The 'Get App' popup is the main blocker, but first we need to CLICK the button.
                browser = p.chromium.launch_persistent_context(
                    user_data_dir=self.user_data_dir,
                    headless=False,
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                    viewport={"width": 1280, "height": 720},
                    args=["--disable-blink-features=AutomationControlled", "--start-maximized"],
                    permissions=["microphone", "camera"]
                )
                
                page = browser.new_page()
                page.goto("https://web.whatsapp.com")
                
                # ... (Login Logic Skipped for brevity in replacement, assume unchanged) ...
                # Actually I must include it or I replace too much. 
                # I will target specific chunks to avoid deleting the login logic.
                
                # ...
                
                # 1. Wait for Login (Main Page Load)
                logger.info("Waiting for WhatsApp to load...")
                # Check for SEARCH BOX (indicator of login)
                try:
                    page.wait_for_selector('div[contenteditable="true"][data-tab="3"]', timeout=45000)
                    logger.info("Logged in successfully.")
                except:
                    qr_path = os.path.join(self.screenshot_dir, "whatsapp_qr.png")
                    page.screenshot(path=qr_path)
                    self.brain.update_history("system", f"WhatsApp needs login! QR at {qr_path}")
                    # Give user time to scan
                    time.sleep(30)
                
                def open_chat(name):
                    logger.info(f"Navigating to {name}...")
                    search_box = page.locator('div[contenteditable="true"][data-tab="3"]')
                    search_box.click()
                    page.keyboard.down("Control")
                    page.keyboard.press("a")
                    page.keyboard.up("Control")
                    page.keyboard.press("Backspace")
                    search_box.fill(name)
                    time.sleep(2)
                    page.keyboard.press("Enter")
                    time.sleep(2)
                    self.active_contact = name

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
                            
                            logger.info(f"Sending queued message: {msg}")
                            page.keyboard.type(msg)
                            time.sleep(0.5)
                            page.keyboard.press("Enter")
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
                                        chat_prompt = f"""
                                        You are TESS, an intelligent assistant having a casual conversation on WhatsApp.{mission_prompt}
                                        
                                        RECENT HISTORY:
                                        {style_context[-1000:]}
                                        
                                        PARTNER JUST SAID: "{text}"
                                        
                                        YOUR GOAL: Reply naturally in the same style (slang, brevity, etc.) while staying focused on the mission.
                                        IMPORTANT: Output ONLY the message text. No JSON, no quotes, no labels.
                                        """
                                        
                                        reply = self.brain.request_completion(
                                            [{"role": "user", "content": chat_prompt}], 
                                            json_mode=False, 
                                            temperature=0.7
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
