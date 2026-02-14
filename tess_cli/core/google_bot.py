import time
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor
from playwright.sync_api import sync_playwright
from .logger import setup_logger

logger = setup_logger("GoogleBot")

# Thread pool for running sync Playwright outside asyncio loop
_executor = ThreadPoolExecutor(max_workers=1)

class GoogleBot:
    """
    Automates Google Services (Gmail, Calendar) using Playwright.
    Connects to an existing Chrome instance or launches a new one with user profile.
    
    IMPORTANT: 
    For this to work without logging in every time, we typically need to point 
    Payload to the user's Chrome User Data directory.
    """
    
    def __init__(self):
        self.headless = False
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        
        # Use project-local data dir to avoid conflicts with system Chrome
        self.user_data_dir = os.path.join(os.getcwd(), "data", "google_session")
        if not os.path.exists(self.user_data_dir):
            os.makedirs(self.user_data_dir, exist_ok=True)
            
    def _start_session_sync(self):
        """Internal sync method that actually starts Playwright."""
        if self.page and not self.page.is_closed():
            return True

        logger.info("Starting GoogleBot Session...")
        self.playwright = sync_playwright().start()
        
        # Launch persistent context
        self.context = self.playwright.chromium.launch_persistent_context(
            user_data_dir=self.user_data_dir,
            headless=self.headless,
            channel="chrome",
            args=[
                "--no-sandbox", 
                "--disable-infobars",
                "--disable-blink-features=AutomationControlled"
            ]
        )
        
        self.page = self.context.pages[0] if self.context.pages else self.context.new_page()
        logger.info("GoogleBot Session Started.")
        return True

    def start_session(self):
        """Starts the browser session. Runs in a thread if an asyncio loop is active."""
        try:
            # Check if we're inside an asyncio event loop
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None
            
            if loop and loop.is_running():
                # Offload to thread to avoid sync_playwright + asyncio conflict
                future = _executor.submit(self._start_session_sync)
                return future.result(timeout=30)
            else:
                return self._start_session_sync()
        except Exception as e:
            logger.error(f"Failed to start GoogleBot session: {e}")
            return False

    def _run_browser_task_sync(self, url, task_callback):
        """Internal sync method for browser tasks."""
        if not self._start_session_sync():
            return "Error: Could not start browser session."
            
        logger.info(f"Navigating to {url}...")
        self.page.goto(url, timeout=60000)
        
        # Run the specific task
        result = task_callback(self.page)
        return result

    def _run_browser_task(self, url, task_callback):
        """
        Generic wrapper to ensure session is running, go to URL, and run task.
        Runs in a thread if an asyncio loop is active.
        """
        try:
            # Check if we're inside an asyncio event loop
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None
            
            if loop and loop.is_running():
                future = _executor.submit(self._run_browser_task_sync, url, task_callback)
                return future.result(timeout=120)
            else:
                return self._run_browser_task_sync(url, task_callback)
                
        except Exception as e:
            logger.error(f"Browser Task Failed: {e}")
            if "Target closed" in str(e):
                self.page = None  # Reset for next retry
                return "Error: Browser closed unexpectedly."
            return f"Error: {e}"

    def stop_session(self):
        """Closes the browser session."""
        try:
            if self.context:
                self.context.close()
            if self.playwright:
                self.playwright.stop()
            self.page = None
            logger.info("GoogleBot Session Stopped.")
        except Exception as e:
            logger.error(f"Error stopping GoogleBot: {e}")

    # ==========================
    # GMAIL OPERATIONS
    # ==========================

    def get_unread_messages(self, max_results=5):
        def task(page):
            # Wait for Gmail to load
            page.wait_for_selector('div[role="main"]', timeout=30000)
            
            # Find unread rows (zA is often the class, but robust selection is better)
            # 'tr.zE' is often unread in standard view
            unread_rows = page.locator('tr.zE').all()
            
            if not unread_rows:
                return "No unread messages found (or selectors changed)."
            
            results = []
            for i, row in enumerate(unread_rows[:max_results]):
                # Extract Sender (often in first cell or specific class)
                # Structure varies. Let's try text extraction.
                text = row.inner_text().replace('\n', ' | ')
                results.append(f"{i+1}. {text}")
                
            return "\n".join(results)

        return self._run_browser_task("https://mail.google.com", task)

    def send_email(self, to_email, subject, body):
        def task(page):
            # Wait for Compose button
            page.wait_for_selector('div[role="button"][jscontroller]', timeout=30000) # Generic wait
            
            # Click Compose (Usually "Compose" text or specific class)
            # Try finding by text "Compose"
            page.get_by_text("Compose").click()
            
            # Wait for "New Message" dialog
            page.wait_for_selector('div[role="dialog"]', timeout=10000)
            
            # Fill To
            page.locator('input[peoplekit-id]').first.fill(to_email)
            page.keyboard.press("Enter")
            
            # Fill Subject (input with name 'subjectbox')
            page.locator('input[name="subjectbox"]').fill(subject)
            
            # Fill Body (div[role="textbox"])
            page.locator('div[role="textbox"]').first.fill(body)
            
            # Click Send (div with text "Send" and role button)
            page.get_by_role("button", name="Send", exact=True).click()
            
            # Wait for "Message sent" notification
            # page.get_by_text("Message sent", exact=False).wait_for()
            time.sleep(2) # Safety wait
            
            return f"Email sent to {to_email}"

        return self._run_browser_task("https://mail.google.com", task)

    # ==========================
    # CALENDAR OPERATIONS
    # ==========================
    
    def list_events(self):
        def task(page):
            # Wait for grid
            page.wait_for_selector('div[role="grid"]', timeout=30000)
            
            # Switch to Schedule View (easier to read) usually by pressing 'a' shortcut or menu
            page.keyboard.press("a") 
            time.sleep(2)
            
            # Read events describe
            # This is hard to scrape generically. Let's precise:
            events = page.locator('div[role="row"]').all()
            
            results = []
            for ev in events[:5]:
                try:
                    results.append(ev.inner_text().replace('\n', ' '))
                except:
                    pass
            
            return "\n".join(results) if results else "No events found (or failed to parse)."

        return self._run_browser_task("https://calendar.google.com", task)

    def create_event(self, text):
        """
        Uses the 'Quick Add' feature if available or simple Create button.
        """
        def task(page):
            # Wait for load
            page.wait_for_selector('body', timeout=30000)
            
            # Keyboard shortcut 'c' usually opens create
            page.keyboard.press("c")
            
            # Wait for dialog
            page.wait_for_selector('div[role="dialog"]', timeout=10000)
            
            # Type title/text
            # Identify title input. Usually focused by default or first input[type=text]
            page.locator('input[type="text"]').first.fill(text)
            
            # Save (often "Save" button)
            page.get_by_role("button", name="Save").click()
            
            time.sleep(2)
            return f"Created event: {text}"

        return self._run_browser_task("https://calendar.google.com", task)
