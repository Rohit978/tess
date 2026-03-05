import pyautogui
import platform
import os
import subprocess
from datetime import datetime
from .logger import setup_logger

logger = setup_logger("SystemController")

class SystemController:
    """
    Controls system functions (Volume, Media, Power) using PyAutoGUI.
    """
    def _safe_run(self, func, *args, **kwargs):
        """Helper to safely run actions with standard error handling."""
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"System Error: {e}")
            return f"Error: {e}"

    def press_key(self, key):
        return self._safe_run(lambda: (pyautogui.press(key), f"Pressed: {key}")[1])

    def type_text(self, text):
        return self._safe_run(lambda: (pyautogui.write(text, interval=0.01), f"Typed: {text}")[1])

    def set_volume(self, action):
        keys = {'up': 'volumeup', 'down': 'volumedown', 'mute': 'volumemute'}
        key = keys.get(action)
        if key:
            return self.press_key(key)
        return "Unknown volume action"

    def media_control(self, action):
        keys = {
            'playpause': 'playpause', 'next': 'nexttrack', 
            'prev': 'prevtrack', 'stop': 'stop'
        }
        key = keys.get(action)
        if key:
            return self.press_key(key)
        return "Unknown media action"

    def take_screenshot(self, filename=None):
        try:
            if not filename:
                filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            
            save_path = os.path.join(os.path.expanduser("~"), "Desktop", filename)
            pyautogui.screenshot(save_path)
            return f"📸 Saved to {save_path}"
        except Exception as e:
            logger.error(f"Screenshot failed: {e}")
            return f"Error: {e}"

    def list_processes(self):
        """Quick process dump via tasklist."""
        try:
            res = subprocess.run(["tasklist", "/FO", "CSV", "/NH"], capture_output=True, text=True)
            procs = sorted(list(set(
                [line.split('","')[0].strip('"') for line in res.stdout.split('\n') if line]
            )))
            return f"Running ({len(procs)}): " + ", ".join(procs[:25]) + "..."
        except Exception as e:
            return f"Failed to list processes: {e}"

    def _win_cmd(self, cmd_str):
        if platform.system() != "Windows": return "OS Not Supported"
        os.system(cmd_str)
        return "Command Sent."

    def lock_system(self):
        return self._win_cmd("rundll32.exe user32.dll,LockWorkStation")

    def sleep_system(self):
        return self._win_cmd("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")

    def shutdown_system(self, restart=False):
        flag = "/r" if restart else "/s"
        return self._win_cmd(f"shutdown {flag} /t 0")
