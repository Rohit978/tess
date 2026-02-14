import pyautogui
import time
import json
import os
import subprocess
from .logger import setup_logger

logger = setup_logger("CallAutomator")

class CallAutomator:
    
    def __init__(self, config_file="call_config.json"):
        self.config_path = os.path.join(os.getcwd(), "src", "core", config_file)
        self.config = self.load_config()

    def load_config(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    return json.load(f)
            except: return {}
        return {}

    def save_config(self):
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=4)

    def calibrate(self, app_name="whatsapp"):
        """
        Interactive CLI method to calibrate coordinates for a specific app.
        Uses a countdown to avoid focus issues with input().
        """
        app_name = app_name.lower()
        print(f"\n--- CALIBRATION FOR: {app_name.upper()} ---")
        print(f"1. Open {app_name.capitalize()} Desktop and open a chat.")
        print("2. Hover your mouse over the 'Search' bar.")
        
        print("\n[READY] I will capture the mouse position in 5 seconds...")
        for i in range(5, 0, -1):
            print(f"Capturing in {i}...", end="\r")
            time.sleep(1)
        
        search_pos = pyautogui.position()
        print(f"\nCaptured Search at: {search_pos}")
        
        print(f"\nNow, hover over the 'Voice Call' button.")
        print("[READY] Capturing in 5 seconds...")
        for i in range(5, 0, -1):
            print(f"Capturing in {i}...", end="\r")
            time.sleep(1)
            
        call_pos = pyautogui.position()
        print(f"\nCaptured Call Button at: {call_pos}")
        
        # Initialize app config if not exists
        if app_name not in self.config:
            self.config[app_name] = {}
            
        self.config[app_name]["search_pos"] = list(search_pos)
        self.config[app_name]["call_pos"] = list(call_pos)
        self.save_config()
        print(f"\nCalibration Saved for {app_name}! You can now use 'call <name> on {app_name}'.")

    def make_call(self, contact_name, app_name="whatsapp"):
        """
        Executes the call sequence using calibrated coordinates for the specific app.
        """
        app_name = app_name.lower()
        
        if app_name not in self.config:
             logger.error(f"App '{app_name}' not configured! Run 'learn call {app_name}' first.")
             return False
             
        app_config = self.config[app_name]
        if "search_pos" not in app_config or "call_pos" not in app_config:
            logger.error(f"Coordinates missing for {app_name}. Run 'learn call {app_name}'.")
            return False

        logger.info(f"Starting Call on {app_name} to: {contact_name}")
        
        # 1. Focus/Launch App
        # Simple URI scheme mapping
        uri_map = {
            "whatsapp": "whatsapp:",
            "telegram": "tg://"
        }
        
        uri = uri_map.get(app_name)
        if uri:
            logger.info(f"Launching via URI: {uri}")
            subprocess.Popen(f"start {uri}", shell=True)
        else:
            logger.warning(f"No URI known for {app_name}, assuming it's open...")
            
        time.sleep(1.5)
        
        # 2. Click Search
        search_x, search_y = app_config["search_pos"]
        pyautogui.click(search_x, search_y)
        time.sleep(0.5)
        
        # 3. Clear and Type
        pyautogui.hotkey('ctrl', 'a')
        pyautogui.press('backspace')
        pyautogui.write(contact_name, interval=0.05)
        time.sleep(1.0)
        
        # 4. Select Contact (Enter)
        pyautogui.press('enter')
        time.sleep(1.0)
        
        # 5. Click Call Button
        call_x, call_y = app_config["call_pos"]
        pyautogui.click(call_x, call_y)
        logger.info(f"Clicked Call Button on {app_name}.")
        
        return True
