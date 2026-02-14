"""
WhatsApp Client - Ported from TESS Terminal Pro.
Uses Playwright with style adaptation and auto-reply.
"""

from playwright.sync_api import sync_playwright
import os
import time
import queue
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger("WhatsAppClient")


class WhatsAppClient:
    def __init__(self, brain, voice_client=None):
        self.brain = brain
        self.voice_client = voice_client
        self.user_data_dir = os.path.join(os.path.expanduser("~"), ".tess", "whatsapp_session_v2")
        os.makedirs(self.user_data_dir, exist_ok=True)
        self.screenshot_dir = os.path.join(os.path.expanduser("~"), ".tess", "screenshots")
        os.makedirs(self.screenshot_dir, exist_ok=True)
        self.msg_queue = queue.Queue()
        self.active_contact = None
        
    def send_message(self, contact, message):
        """Queue a message for a specific contact."""
        logger.info(f"Queuing for {contact}: {message}")
        self.msg_queue.put({"contact": contact, "message": message, "action": "send"})

    def send_message_sync(self, contact, message):
        """Send a message synchronously (one-shot, no monitor needed)."""
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch_persistent_context(
                    user_data_dir=self.user_data_dir,
                    channel="chrome",
                    headless=False,
                    viewport=None,
                    args=["--start-maximized", "--disable-blink-features=AutomationControlled", "--disable-gpu", "--no-sandbox"],
                    ignore_default_args=["--enable-automation"]
                )
                page = browser.new_page()
                page.goto("https://web.whatsapp.com", timeout=60000, wait_until="domcontentloaded")
                
                # Wait for login
                try:
                    page.wait_for_selector('div[contenteditable="true"][data-tab="3"]', timeout=60000)
                    logger.info("Logged in successfully.")
                except:
                    qr_path = os.path.join(self.screenshot_dir, "whatsapp_qr.png")
                    page.screenshot(path=qr_path)
                    logger.warning(f"WhatsApp needs login! QR at {qr_path}")
                    time.sleep(30)
                
                # Search for contact
                search_box = page.locator('div[contenteditable="true"][data-tab="3"]')
                search_box.click()
                page.keyboard.down("Control")
                page.keyboard.press("a")
                page.keyboard.up("Control")
                page.keyboard.press("Backspace")
                search_box.fill(contact)
                time.sleep(2)
                page.keyboard.press("Enter")
                time.sleep(2)
                
                # Type and send
                page.keyboard.type(message)
                time.sleep(0.5)
                page.keyboard.press("Enter")
                
                time.sleep(2)
                browser.close()
                return f"✓ Message sent to {contact}"
                
        except Exception as e:
            logger.error(f"Send error: {e}")
            return f"Send error: {e}"

    def monitor_loop(self, contact_name, mission=None, stop_event=None):
        """
        Runs the WhatsApp monitor.
        Accepts a 'mission' to keep conversation focused.
        """
        self.active_contact = contact_name
        logger.info(f"Starting WhatsApp Monitor for: {contact_name} (Mission: {mission})")
        
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch_persistent_context(
                    user_data_dir=self.user_data_dir,
                    channel="chrome",
                    headless=False,
                    viewport=None,
                    args=["--start-maximized", "--disable-blink-features=AutomationControlled", "--disable-gpu", "--no-sandbox"],
                    ignore_default_args=["--enable-automation"],
                    permissions=["microphone", "camera"]
                )
                
                page = browser.new_page()
                page.goto("https://web.whatsapp.com")
                
                # 1. Wait for Login
                logger.info("Waiting for WhatsApp to load...")
                try:
                    page.wait_for_selector('div[contenteditable="true"][data-tab="3"]', timeout=60000)
                    logger.info("Logged in successfully.")
                except:
                    qr_path = os.path.join(self.screenshot_dir, "whatsapp_qr.png")
                    page.screenshot(path=qr_path)
                    if self.brain:
                        self.brain.update_history("system", f"WhatsApp needs login! QR at {qr_path}")
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
                
                # Initial history load for style adaptation
                logger.info("Analyzing chat history for style adaptation (reading last 10 msgs)...")
                try:
                    history_rows = page.locator('div[role="row"]').all()
                    recent_rows = history_rows[-10:]
                    
                    chat_log = []
                    
                    for row in recent_rows:
                        is_me = row.locator('.message-out').count() > 0
                        sender = "Me" if is_me else self.active_contact
                        
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
                            
                            if target and target != self.active_contact:
                                open_chat(target)
                            
                            logger.info(f"Sending queued message: {msg}")
                            page.keyboard.type(msg)
                            time.sleep(0.5)
                            page.keyboard.press("Enter")
                            if self.brain:
                                self.brain.update_history("system", f"Sent to {self.active_contact}: {msg}")
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
                                    text = last_row.inner_text().split('\n')[0].strip()
                                        
                                    # Only reply if it's NEW
                                    if text and text != last_msg_text:
                                        logger.info(f"New Message from {self.active_contact}: {text}")
                                        last_msg_text = text
                                        
                                        if self.brain:
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
                                        
                                        if self.brain:
                                            reply = self.brain.request_completion(
                                                [{"role": "user", "content": chat_prompt}], 
                                                json_mode=False, 
                                                temperature=0.7
                                            )
                                        else:
                                            reply = "I'm sorry, I can't reply right now (Brain disconnected)."
                                        
                                        if reply:
                                            logger.info(f"Typing reply: {reply}")
                                            page.keyboard.type(reply)
                                            time.sleep(0.5)
                                            page.keyboard.press("Enter")
                                            last_msg_text = reply
                                            style_context += f"\nMe: {reply}"
                                        else:
                                            logger.warning("Brain did not return a reply.")
                                except Exception as e:
                                    logger.error(f"Error extracting text: {e}")
                        
                        time.sleep(2)  # Poll interval
                        
                    except Exception as loop_e:
                        logger.error(f"Monitor Loop Error: {loop_e}")
                        
                        err_str = str(loop_e).lower()
                        if "target closed" in err_str or "connection closed" in err_str or "browser has been closed" in err_str:
                            logger.error("Browser seems closed! Exiting Monitor.")
                            break
                        
                        time.sleep(5)
                        
                logger.info("Stopping WhatsApp Monitor...")
                browser.close()
                
            except Exception as e:
                logger.error(f"WhatsApp Fatal Error: {e}")
                if self.brain:
                    self.brain.update_history("system", f"WhatsApp Monitor failed: {e}")
