import pyautogui
import time
import subprocess
import os
from .logger import setup_logger

logger = setup_logger("WhatsAppDesktop")

class WhatsAppDesktop:
    """
    Automates the WhatsApp Desktop Application (Windows) specifically for making calls.
    Uses pyautogui for keyboard shortcuts and visual navigation.
    
    Requirements:
    - WhatsApp Desktop for Windows installed (Store or Exe version) and Logged In.
    - App must be accessible via Start Menu or 'whatsapp:' URI.
    """
    
    def __init__(self):
        self.os_name = os.name
        # Confidence thresholds for image matching (if we use images later)
        self.confidence = 0.8 

    def launch_app(self):
        """Launches or focuses the WhatsApp Desktop app."""
        logger.info("Launching/Focusing WhatsApp Desktop...")
        try:
            # Try efficient method first: Request via URI protocol
            # This works for both Store and Exe versions usually
            subprocess.Popen(["start", "whatsapp:"], shell=True)
            time.sleep(2) # Wait for window to appear
            return True
        except Exception as e:
            logger.error(f"Failed to launch via URI: {e}")
            return False

    def make_call(self, contact_name, video=False):
        """
        Initiates a call to the specified contact using Desktop Automation.
        
        Flow:
        1. Open App
        2. Ctrl+F (Search)
        3. Type Name + Enter (Open Chat)
        4. Ctrl+Shift+C (Audio Call) or Ctrl+Shift+V (Video Call)
           * Note: Shortcuts might vary by version, we will try standard ones.
        """
        logger.info(f"Attempting Desktop Call to: {contact_name}")
        
        if not self.launch_app():
            return False
            
        # Give it a moment to settle focus
        time.sleep(1.5)
        
        # 1. Search for Contact
        # Ctrl + F is standard for Search in WhatsApp Desktop
        logger.info("Searching for contact...")
        pyautogui.hotkey('ctrl', 'f')
        time.sleep(0.5)
        
        # Clear previous search if any (Ctrl+A -> Backspace)
        pyautogui.hotkey('ctrl', 'a')
        pyautogui.press('backspace')
        time.sleep(0.3)
        
        # Type Name
        pyautogui.write(contact_name, interval=0.05)
        time.sleep(1.0) # Wait for search results
        
        # Select first result (Down -> Enter or just Enter if it auto-selects top)
        # Usually Enter selects the top result
        pyautogui.press('enter')
        time.sleep(1.0) # Wait for chat to load
        
        # 2. Initiate Call
        # Shortcuts:
        # Audio Call: Ctrl + Shift + C
        # Video Call: Ctrl + Shift + V
        
        logger.info(f"Triggering {'Video' if video else 'Audio'} Call shortcut...")
        
        if video:
            pyautogui.hotkey('ctrl', 'shift', 'v')
        else:
            pyautogui.hotkey('ctrl', 'shift', 'c')
            
        time.sleep(1)
        
        # Check for potential confirmations (unlikely with shortcuts, but possible)
        # For now, we assume success if no error occurred.
        logger.info("Call shortcut sent.")
        return True
