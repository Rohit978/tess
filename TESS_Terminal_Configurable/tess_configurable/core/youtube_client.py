"""
YouTube Client - Control YouTube playback.
Uses Selenium for browser control.
"""

import time
import urllib.parse
from typing import Optional


class YouTubeClient:
    """
    Controls YouTube playback via Selenium.
    """
    
    def __init__(self, headless: bool = False):
        self.headless = headless
        self.driver = None
        self.current_video = None
    
    def _ensure_driver(self):
        """Ensure WebDriver is initialized."""
        if not self.driver:
            try:
                from selenium import webdriver
                from selenium.webdriver.chrome.options import Options
                from selenium.webdriver.chrome.service import Service
                from webdriver_manager.chrome import ChromeDriverManager
                
                options = Options()
                if self.headless:
                    options.add_argument("--headless")
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=options)
                
            except Exception as e:
                print(f"YouTube driver init failed: {e}")
                return False
        return True
    
    def play_video(self, query: str) -> str:
        """
        Search and play a YouTube video.
        
        Args:
            query: Video search query
            
        Returns:
            Status message
        """
        if not self._ensure_driver():
            # Fallback: open in default browser
            import webbrowser
            encoded = urllib.parse.quote(query)
            url = f"https://www.youtube.com/results?search_query={encoded}"
            webbrowser.open(url)
            return f"Opened YouTube search for: {query}"
        
        try:
            # Search YouTube
            encoded = urllib.parse.quote(query)
            url = f"https://www.youtube.com/results?search_query={encoded}"
            
            self.driver.get(url)
            time.sleep(3)
            
            # Click first video
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            
            # Wait for video links
            video = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "ytd-video-renderer #video-title"))
            )
            
            video.click()
            self.current_video = query
            
            return f"Playing: {query}"
            
        except Exception as e:
            return f"YouTube error: {e}"
    
    def control(self, action: str) -> str:
        """
        Control playback.
        
        Args:
            action: play, pause, next, mute, vol_up, vol_down
            
        Returns:
            Status message
        """
        if not self.driver:
            return "YouTube not initialized"
        
        try:
            from selenium.webdriver.common.by import By
            
            if action in ["play", "pause", "play_pause"]:
                # Click video to toggle play/pause
                video = self.driver.find_element(By.CSS_SELECTOR, "video")
                video.click()
                return f"Toggled play/pause"
            
            elif action == "mute":
                # Try to find mute button
                try:
                    mute_btn = self.driver.find_element(By.CSS_SELECTOR, "button.ytp-mute-button")
                    mute_btn.click()
                    return "Toggled mute"
                except:
                    return "Mute button not found"
            
            elif action == "next":
                try:
                    next_btn = self.driver.find_element(By.CSS_SELECTOR, "a.ytp-next-button")
                    next_btn.click()
                    return "Next video"
                except:
                    return "Next button not found"
            
            elif action == "fullscreen":
                try:
                    fs_btn = self.driver.find_element(By.CSS_SELECTOR, "button.ytp-fullscreen-button")
                    fs_btn.click()
                    return "Toggled fullscreen"
                except:
                    return "Fullscreen button not found"
            
            else:
                return f"Unknown action: {action}"
                
        except Exception as e:
            return f"Control error: {e}"
    
    def close(self):
        """Close browser."""
        if self.driver:
            self.driver.quit()
            self.driver = None
