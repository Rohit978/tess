import logging
import time
import os
import threading
from playwright.sync_api import sync_playwright
from .terminal_ui import C

logger = logging.getLogger("YouTubeClient")

class YouTubeClient:
    """
    Automates YouTube Web using Playwright.
    Supports playing videos by search query and controlling playback.
    """
    def __init__(self, headless=False):
        self.headless = headless
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.is_running = False
        
        # User Data Dir for persistence (cookies, login)
        self.user_data_dir = os.path.join(os.getcwd(), "data", "youtube_session")
        if not os.path.exists(self.user_data_dir):
            os.makedirs(self.user_data_dir)

    def is_page_active(self):
        try:
            return self.page and not self.page.is_closed()
        except:
            return False

    def start_session(self):
        """Starts the browser session if not already running."""
        try:
            if self.is_page_active():
                return

            logger.info(f"Starting YouTube Session (Headless={self.headless})...")
            print(f"  {C.DIM}🌐 Starting YouTube Session (Headless={self.headless})...{C.R}")
            
            if not self.playwright:
                 self.playwright = sync_playwright().start()
            
            # Launch persistent context
            try:
                self.context = self.playwright.chromium.launch_persistent_context(
                    user_data_dir=self.user_data_dir,
                    headless=self.headless,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-web-security",
                        "--disable-features=IsolateOrigins,site-per-process"
                    ]
                )
            except Exception as e:
                logger.error(f"Persistent browser launch failed: {e}. Retrying with temporary profile...")
                print(f"  {C.YELLOW}⚠️ Persistent profile locked/failed. Retrying with temporary profile...{C.R}")
                # Fallback to temporary context (no user data)
                try:
                    browser = self.playwright.chromium.launch(
                        headless=self.headless,
                        args=["--disable-blink-features=AutomationControlled"]
                    )
                    self.context = browser.new_context()
                    self.browser = browser # Keep reference
                except Exception as fallback_err:
                    logger.critical(f"Fallback launch failed: {fallback_err}")
                    raise fallback_err
            
            self.page = self.context.pages[0] if self.context.pages else self.context.new_page()
            logger.info("Navigating to YouTube...")
            print(f"  {C.DIM}🌐 Navigating to YouTube...{C.R}")
            
            try:
                self.page.goto("https://www.youtube.com", timeout=60000)
            except Exception as nav_err:
                logger.warning(f"Navigation timeout/error: {nav_err}")
                # We continue anyway, might be just slow load
            
            # Handle Cookie Consent
            self._handle_consent()

            self.is_running = True
            logger.info("YouTube Session Started Successfully.")

        except Exception as e:
            logger.error(f"Critical YouTube Start Error: {e}", exc_info=True)
            self.is_running = False
            raise e

    def _handle_consent(self):
        try:
            # Check for "Before you continue to YouTube" or "I agree" buttons
            consent_selectors = [
                'button[aria-label="Accept all"]',
                'button[aria-label="Accept the use of cookies and other data for the purposes described"]',
                '#content .vjs-button',
                'button:has-text("Accept all")',
                'button:has-text("I agree")'
            ]
            
            for selector in consent_selectors:
                if self.page.locator(selector).count() > 0:
                    try:
                        self.page.click(selector, timeout=2000)
                        logger.info(f"Clicked consent: {selector}")
                        time.sleep(1)
                        break
                    except: pass
        except Exception as ce:
            logger.debug(f"Consent check skipped/failed: {ce}")

    def play_video(self, query):
        """Searches for a video and plays the first result."""
        try:
            # 1. Check if browser is alive, otherwise restart
            if not self.is_page_active():
                self.start_session()
            
            # 2. Ensure we are on YouTube (prevent sticking on old page or about:blank)
            try:
                if "youtube.com" not in self.page.url:
                    print(f"  {C.DIM}🌐 Refreshing YouTube...{C.R}")
                    self.page.goto("https://www.youtube.com", timeout=30000)
            except: pass
            
            print(f"  {C.DIM}🔎 YouTube Search: {query}{C.R}")
            
            # Search Input - Try robust locators
            # 1. Try placeholder text (most reliable for i18n/DOM changes)
            search_input = self.page.get_by_placeholder("Search").first
            
            if not search_input.is_visible():
                # 2. Try generic ID fallback
                search_input = self.page.locator('input#search').first
            
            if not search_input.is_visible():
                # 3. Try clicking the search icon first (mobile view or collapsed)
                search_icon = self.page.get_by_role("button", name="Search").first
                if search_icon.is_visible():
                    search_icon.click()
                    time.sleep(0.5)
            
            if not search_input.is_visible():
                print(f"  {C.RED}❌ Search input still not visible. Page might be blocked or changed.{C.R}")
                return "Error: Could not find search input."

            search_input.click()
            search_input.fill(query)
            search_input.press("Enter")
            
            # Wait for results to load
            print(f"  {C.DIM}⏳ Waiting for search results...{C.R}")
            try:
                # Wait for any video title to appear
                self.page.wait_for_selector('a#video-title', timeout=15000)
            except Exception as e:
                print(f"  {C.RED}❌ Search results didn't load in time.{C.R}")
                return f"No results found for '{query}'"

            # Click first video result
            # We want the first REAL video, not a shelf, ad, or channel
            # We enforce `a#video-title` to skip shelves
            video_titles = self.page.locator("a#video-title")
            
            # Wait for at least one
            video_titles.first.wait_for(state="visible", timeout=10000)
            
            if video_titles.count() > 0:
                first_video = video_titles.first
                title_text = first_video.inner_text().strip()
                if not title_text:
                    title_text = first_video.get_attribute('title') or "Video"
                    
                print(f"  {C.GREEN}▶️ Found video: {title_text}{C.R}")
                
                # Try clicking the element directly, fallback to forcing via JS
                try:
                    first_video.click(timeout=3000)
                except:
                    first_video.evaluate("node => node.click()")
                    
                return f"Playing: {title_text}"

            else:
                print(f"  {C.YELLOW}⚠️ No video titles found in results.{C.R}")
                return "No video results found."
                
        except Exception as e:
            print(f"  {C.RED}🔥 Error in play_video: {e}{C.R}")
            import traceback
            traceback.print_exc()
            return f"Error: {e}"


    def control(self, action):
        """
        Controls playback using keyboard shortcuts.
        action: pause, play, next, prev, mute, vol_up, vol_down, skip_ad
        """
        if not self.page or self.page.is_closed():
            return "YouTube is not running."
            
        try:
            # Focus on the player or body
            self.page.click("body") 
            
            if action in ["play", "pause"]:
                self.page.keyboard.press("k") # k toggles play/pause
            elif action == "next":
                self.page.keyboard.press("Shift+N") # Next video
            elif action == "prev":
                self.page.keyboard.press("PreviousTrack") # Browser back or prev (shift+p)
            elif action == "mute":
                self.page.keyboard.press("m")
            elif action == "vol_up":
                self.page.keyboard.press("ArrowUp")
            elif action == "vol_down":
                self.page.keyboard.press("ArrowDown")
            elif action == "fullscreen":
                self.page.keyboard.press("f")
            elif action == "skip_ad":
                # Try locating "Skip Ad" button
                skip_btn = self.page.locator(".ytp-ad-skip-button")
                if skip_btn.count() > 0:
                    skip_btn.click()
                    return "Skipped Ad."
                else:
                    return "No ad skip button found."
            else:
                return f"Unknown action: {action}"
                
            return f"Executed: {action}"
            
        except Exception as e:
            logger.error(f"Error executing control {action}: {e}")
            return f"Error: {e}"

    def stop(self):
        """Closes the browser session."""
        try:
            if self.context:
                self.context.close()
            if self.playwright:
                self.playwright.stop()
            self.is_running = False
            logger.info("YouTube Session Stopped.")
        except Exception as e:
            logger.error(f"Error stopping YouTube: {e}")
