import pyautogui
from .logger import setup_logger

logger = setup_logger("SystemController")

class SystemController:
    """
    Controls system functions like Volume and Media using PyAutoGUI.
    """
    
    def press_key(self, key):
        """Simulate a single key press."""
        try:
            pyautogui.press(key)
            return f"Pressed key: {key}"
        except Exception as e:
            logger.error(f"Press key error: {e}")
            return f"Error: {e}"

    def type_text(self, text):
        """Simulate typing text."""
        try:
            pyautogui.write(text, interval=0.01)
            return f"Typed text: {text}"
        except Exception as e:
            logger.error(f"Type text error: {e}")
            return f"Error: {e}"

    def set_volume(self, action):
        """
        Adjusts volume.
        action: 'up', 'down', 'mute'
        """
        try:
            if action == 'up':
                pyautogui.press('volumeup')
                return "Volume Increased"
            elif action == 'down':
                pyautogui.press('volumedown')
                return "Volume Decreased"
            elif action == 'mute':
                pyautogui.press('volumemute')
                return "Volume Muted/Unmuted"
            return "Unknown volume action"
        except Exception as e:
            logger.error(f"Volume error: {e}")
            return f"Error: {e}"

    def media_control(self, action):
        """
        Controls media playback.
        action: 'playpause', 'next', 'prev', 'stop'
        """
        try:
            if action == 'playpause':
                pyautogui.press('playpause')
                return "Media Play/Pause"
            elif action == 'next':
                pyautogui.press('nexttrack')
                return "Next Track"
            elif action == 'prev':
                pyautogui.press('prevtrack')
                return "Previous Track"
            elif action == 'stop':
                pyautogui.press('stop')
                return "Media Stop"
            return "Unknown media action"
        except Exception as e:
            logger.error(f"Media error: {e}")
            return f"Error: {e}"

    def take_screenshot(self, filename=None):
        """
        Takes a screenshot.
        """
        import os
        from datetime import datetime
        try:
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"screenshot_{timestamp}.png"
                
            # Save to desktop or temp
            save_path = os.path.join(os.path.expanduser("~"), "Desktop", filename)
            pyautogui.screenshot(save_path)
            return f"Screenshot saved to {save_path}"
        except Exception as e:
            logger.error(f"Screenshot error: {e}")
            return f"Error: {e}"

    def list_processes(self):
        """
        Lists running processes (Top 20 by memory or just generic list).
        Uses 'tasklist' command for Windows compatibility without extra deps (like psutil).
        """
        import subprocess
        try:
            # Get list of running processes
            result = subprocess.run(["tasklist", "/FO", "CSV", "/NH"], capture_output=True, text=True)
            output = result.stdout.strip()
            
            # Parse CSV
            processes = []
            for line in output.split('\n'):
                if not line: continue
                parts = line.split('","')
                if len(parts) >= 1:
                    name = parts[0].strip('"')
                    pid = parts[1].strip('"') if len(parts) > 1 else "?"
                    mem = parts[4].strip('"') if len(parts) > 4 else "?"
                    processes.append(f"{name} (PID: {pid}, Mem: {mem})")
            
            # Return summary (unique names to avoid spamming chrome.exe x100)
            unique_procs = sorted(list(set([p.split()[0] for p in processes])))
            
            count = len(unique_procs)
            top_list = ", ".join(unique_procs[:30]) # Limit to 30 for brevity
            
            return f"Running Processes ({count} unique apps): {top_list}..."
        except Exception as e:
            logger.error(f"List Process error: {e}")
            return f"Error listing processes: {e}"

    def lock_system(self):
        """Lock the workstation."""
        import os
        import platform
        if platform.system() == "Windows":
            os.system("rundll32.exe user32.dll,LockWorkStation")
            return "System Locked"
        return "Lock not supported on this OS"

    def sleep_system(self):
        """Put system to sleep."""
        import os
        import platform
        if platform.system() == "Windows":
            os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
            return "System Sleeping..."
        return "Sleep not supported"

    def shutdown_system(self, restart=False):
        """Shutdown or restart system."""
        import os
        import platform
        if platform.system() == "Windows":
            cmd = "shutdown /r /t 0" if restart else "shutdown /s /t 0"
            os.system(cmd)
            return "System Restarting..." if restart else "System Shutting Down..."
        return "Shutdown not supported"
