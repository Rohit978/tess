import subprocess
import time
import threading
import sys
from .logger import setup_logger

logger = setup_logger("ClipboardSync")

# Windows specific flag to prevent command prompt popups on background runs
CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0

class ClipboardSyncMonitor:
    """
    Background worker that monitors the PC clipboard for changes and pushes updates
    to the SSE stream. Also allows updating the local PC clipboard from a remote device.
    Uses silent PowerShell calls to ensure zero dependencies and complete portability on Windows.
    """
    def __init__(self, on_change_callback):
        self.on_change_callback = on_change_callback
        self.last_clipboard = ""
        self.running = False
        self.thread = None

    def get_clipboard(self) -> str:
        try:
            if sys.platform != "win32":
                return ""
            res = subprocess.run(
                ["powershell", "-NoProfile", "-Command", "Get-Clipboard"],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=CREATE_NO_WINDOW
            )
            return (res.stdout or "").strip()
        except Exception as e:
            logger.error(f"Failed to get clipboard: {e}")
            return ""

    def set_clipboard(self, text: str):
        try:
            if sys.platform != "win32":
                return
            import base64
            # Base64 encode to safely handle emojis, special chars, and escape sequences in PowerShell
            b64_text = base64.b64encode(text.encode('utf-8')).decode('utf-8')
            script = f"[System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String('{b64_text}')) | Set-Clipboard"
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", script],
                check=True,
                timeout=5,
                creationflags=CREATE_NO_WINDOW
            )
            self.last_clipboard = text
            logger.info("Local clipboard set successfully.")
        except Exception as e:
            logger.error(f"Failed to set clipboard: {e}")

    def start(self):
        if self.running:
            return
        if sys.platform != "win32":
            logger.warning("Clipboard Sync only supported on Windows.")
            return
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True, name="ClipboardSyncMonitor")
        self.thread.start()
        logger.info("Clipboard Sync Monitor started.")

    def stop(self):
        self.running = False
        logger.info("Clipboard Sync Monitor stopped.")

    def _run_loop(self):
        while self.running:
            try:
                current = self.get_clipboard()
                if current and current != self.last_clipboard:
                    self.last_clipboard = current
                    logger.info("Local clipboard change detected.")
                    self.on_change_callback(current)
            except Exception as e:
                logger.error(f"Clipboard loop error: {e}")
            time.sleep(2)  # Poll every 2 seconds
