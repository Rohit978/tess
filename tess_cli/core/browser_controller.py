import pyautogui
import time
import subprocess
from .logger import setup_logger

logger = setup_logger("BrowserController")

class BrowserController:
    """
    Controls browser tabs using keyboard shortcuts via PyAutoGUI.
    Assumes browser window is active or can be activated.
    """
    
    def __init__(self):
        # Fail-safe to move mouse to corner to abort
        pyautogui.FAILSAFE = True
        
    def focus_browser(self, browser_name="Any"):
        """
        Attempts to bring a browser window to the front.
        Currently simplistic: Assumes user just opened it or it's active.
        TODO: Use pywin32 to specifically target 'Chrome' or 'Edge' window titles.
        """
        pass # Rely on user having it open for now, or use AppLauncher first

    def new_tab(self, url=None):
        """Open new tab, optionally navigate to URL."""
        try:
            logger.info("Opening new tab...")
            pyautogui.hotkey('ctrl', 't')
            time.sleep(0.5)
            
            if url:
                self.go_to_url(url)
            return "Opened new tab"
        except Exception as e:
            return f"Error opening tab: {e}"

    def close_tab(self):
        """Close current tab."""
        try:
            logger.info("Closing tab...")
            pyautogui.hotkey('ctrl', 'w')
            return "Closed current tab"
        except Exception as e:
            return f"Error closing tab: {e}"

    def next_tab(self):
        """Switch to next tab."""
        try:
            pyautogui.hotkey('ctrl', 'tab')
            return "Switched to next tab"
        except Exception as e:
            return f"Error switching tab: {e}"

    def prev_tab(self):
        """Switch to previous tab."""
        try:
            pyautogui.hotkey('ctrl', 'shift', 'tab')
            return "Switched to previous tab"
        except Exception as e:
            return f"Error switching tab: {e}"

    def go_to_url(self, url):
        """Focus address bar and type URL."""
        try:
            logger.info(f"Navigating to {url}...")
            pyautogui.hotkey('ctrl', 'l')
            time.sleep(0.2)
            pyautogui.write(url)
            time.sleep(0.1)
            pyautogui.press('enter')
            return f"Navigated to {url}"
        except Exception as e:
            return f"Error navigating: {e}"
