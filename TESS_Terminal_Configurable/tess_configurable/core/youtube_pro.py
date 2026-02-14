"""
YouTube Client - Ported from TESS Terminal Pro.
Automates YouTube Web using Playwright.
Supports playing videos by search query and controlling playback.
"""

import logging
import time
import os
from playwright.sync_api import sync_playwright

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
        self.user_data_dir = os.path.join(os.path.expanduser("~"), ".tess", "youtube_session")
        if not os.path.exists(self.user_data_dir):
            os.makedirs(self.user_data_dir)

    def start_session(self):
        """Starts the browser session if not already running."""
        if self.page and not self.page.is_closed():
            return

        logger.info("Starting YouTube Session...")
        self.playwright = sync_playwright().start()
        
        # Launch persistent context
        self.context = self.playwright.chromium.launch_persistent_context(
            user_data_dir=self.user_data_dir,
            headless=self.headless,
            args=["--disable-blink-features=AutomationControlled"]
        )
        
        self.page = self.context.pages[0] if self.context.pages else self.context.new_page()
        self.page.goto("https://www.youtube.com")
        self.is_running = True
        logger.info("YouTube Session Started.")

    def play_video(self, query):
        """Searches for a video and plays the first result."""
        try:
            self.start_session()
            
            logger.info(f"Searching for: {query}")
            
            # Wait for search input
            try:
                self.page.wait_for_selector('input[name="search_query"], input#search', timeout=10000)
            except:
                logger.warning("Search input not found within timeout.")

            # Standard search input
            search_input = self.page.locator('input[name="search_query"]').first
            
            # Fallback
            if not search_input.is_visible():
                search_input = self.page.locator('input#search').first
                
            search_input.click()
            search_input.fill(query)
            search_input.press("Enter")
            
            time.sleep(3)  # Wait for page load
            
            # Click first video result
            video_title = self.page.locator("ytd-video-renderer #video-title").first
            
            video_title.wait_for(state="visible", timeout=10000)
            
            if video_title.count() > 0:
                title_text = video_title.inner_text()
                logger.info(f"Playing: {title_text}")
                video_title.click()
            else:
                logger.warning("No video results found.")
                return "No video results found."
                
            return f"Playing: {title_text}"
            
        except Exception as e:
            logger.error(f"Error playing video: {e}")
            return f"Error: {e}"

    def control(self, action):
        """
        Controls playback using keyboard shortcuts.
        action: pause, play, next, prev, mute, vol_up, vol_down, skip_ad
        """
        if not self.page or self.page.is_closed():
            return "YouTube is not running."
            
        try:
            self.page.click("body") 
            
            if action in ["play", "pause"]:
                self.page.keyboard.press("k")
            elif action == "next":
                self.page.keyboard.press("Shift+N")
            elif action == "prev":
                self.page.keyboard.press("PreviousTrack")
            elif action == "mute":
                self.page.keyboard.press("m")
            elif action == "vol_up":
                self.page.keyboard.press("ArrowUp")
            elif action == "vol_down":
                self.page.keyboard.press("ArrowDown")
            elif action == "fullscreen":
                self.page.keyboard.press("f")
            elif action == "skip_ad":
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
