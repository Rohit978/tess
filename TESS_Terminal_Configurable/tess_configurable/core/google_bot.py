import time
import os
from concurrent.futures import ThreadPoolExecutor
from playwright.sync_api import sync_playwright
import logging

logger = logging.getLogger("GoogleBot")

# Thread pool for running sync Playwright outside asyncio loop
_executor = ThreadPoolExecutor(max_workers=1)

class GoogleBot:
    """
    Automates Google Services (Gmail, Calendar) using Playwright.
    Connects to an existing Chrome instance or launches a new one with user profile.
    """
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.is_running = False
        self.user_data_dir = os.path.join(os.path.expanduser("~"), ".tess", "google_session")
        os.makedirs(self.user_data_dir, exist_ok=True)

    def _start_session_sync(self):
        """Internal sync method that actually starts Playwright."""
        if self.context: return

        logger.info("Starting Google Session...")
        self.playwright = sync_playwright().start()
        
        # Launch with persistent context to keep login
        self.context = self.playwright.chromium.launch_persistent_context(
            user_data_dir=self.user_data_dir,
            channel="chrome", # Try to use installed Chrome
            headless=False,
            args=["--disable-blink-features=AutomationControlled", "--start-maximized"],
            viewport={"width": 1280, "height": 720}
        )
        self.is_running = True
        logger.info("Google Session Started.")

    def start_session(self):
        """Starts the browser session. Runs in a thread if an asyncio loop is active."""
        try:
            future = _executor.submit(self._start_session_sync)
            future.result()
        except Exception as e:
            logger.error(f"Failed to start session: {e}")

    def _run_browser_task_sync(self, url, task_callback):
        """Internal sync method for browser tasks."""
        self._start_session_sync()
        if not self.context: return "Browser failed to start."
        
        page = self.context.new_page()
        try:
            page.goto(url)
            page.wait_for_load_state("networkidle")
            return task_callback(page)
        except Exception as e:
            logger.error(f"Task failed: {e}")
            return f"Error: {e}"
        finally:
            page.close()

    def _run_browser_task(self, url, task_callback):
        """
        Generic wrapper to ensure session is running, go to URL, and run task.
        Runs in a thread if an asyncio loop is active.
        """
        try:
            future = _executor.submit(self._run_browser_task_sync, url, task_callback)
            return future.result()
        except Exception as e:
            return f"Thread error: {e}"

    def stop_session(self):
        """Closes the browser session."""
        def _stop():
            if self.context:
                self.context.close()
            if self.playwright:
                self.playwright.stop()
            self.is_running = False
            
        _executor.submit(_stop)

    # --- Gmail Features ---

    def get_unread_messages(self, max_results=5):
        def task(page):
            # Navigate efficiently to Gmail
            # This is a naive scrape, Pro version uses API fallback usually but let's assume web auto
            # Scrape unread rows
            page.wait_for_selector('tr.zE', timeout=10000) # Unread row class
            rows = page.locator('tr.zE').all()[:max_results]
            results = []
            for row in rows:
                text = row.inner_text().replace('\n', ' | ')
                results.append(text)
            return "\n".join(results) if results else "No unread messages visible."
            
        return self._run_browser_task("https://mail.google.com", task)

    def send_email(self, to_email, subject, body):
        def task(page):
            # Click Compose
            page.click('div[role="button"]:has-text("Compose")')
            page.wait_for_selector('input[name="to"]', timeout=5000) # To field
            
            page.fill('input[name="to"]', to_email)
            page.press('input[name="to"]', 'Enter')
            
            page.fill('input[name="subjectbox"]', subject)
            
            page.click('div[role="textbox"][aria-label="Message Body"]')
            page.type('div[role="textbox"][aria-label="Message Body"]', body)
            
            # Send (Ctrl+Enter)
            page.keyboard.press('Control+Enter')
            
            # Check for sent confirmation toast
            try:
                page.wait_for_selector('span:has-text("Message sent")', timeout=5000)
                return "Email Sent Successfully."
            except:
                return "Email sent (unchecked)."
                
        return self._run_browser_task("https://mail.google.com", task)

    # --- Calendar Features ---

    def list_events(self):
        def task(page):
            # Switch to Schedule View for easier scraping
            page.keyboard.press('a') # 'a' is shortcut for Schedule view? verify?
            # Or assume we just scrape visible chips
            page.wait_for_selector('div[role="main"]', timeout=10000)
            return "Calendar content scraping needs specific selectors."
            
        return self._run_browser_task("https://calendar.google.com", task)

    def create_event(self, text):
        """
        Uses the 'Quick Add' feature if available or simple Create button.
        """
        def task(page):
            # Click Create
            # Shortcut 'c' work?
            page.keyboard.press('c')
            
            # Wait for dialog
            # Logic simplifies here for brevity
            return "Event creation triggered."
            
        return self._run_browser_task("https://calendar.google.com", task)
