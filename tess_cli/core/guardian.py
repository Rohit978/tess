import time
import threading
from .logger import setup_logger
from .config import Config

logger = setup_logger("Guardian")

class Guardian:
    """
    [EXPERIMENTAL] The Privacy Aura.
    Monitors for strangers using computer vision and locks down the system.
    """
    def __init__(self, sys_ctrl):
        self.sys_ctrl = sys_ctrl
        self.active = False
        self.monitor_thread = None
        self._stranger_detected = False

    def toggle(self, enable=True):
        if enable and not self.active:
            self.active = True
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitor_thread.start()
            logger.info("🛡️ Privacy Aura ACTIVATED.")
            return "Privacy Aura is now ON. Guardian is watching."
        elif not enable and self.active:
            self.active = False
            logger.info("🔓 Privacy Aura DEACTIVATED.")
            return "Privacy Aura is now OFF."
        return f"Privacy Aura is already {'ON' if self.active else 'OFF'}."

    def _monitor_loop(self):
        """
        Background loop to detect strangers.
        Placeholder for real OpenCV / Face Recognition logic.
        """
        while self.active:
            # 1. Check if module is still enabled in global config
            if not Config.is_module_enabled("privacy_aura"):
                self.active = False
                break

            # 2. Simulate detection (In reality, this uses cv2.VideoCapture)
            # For the demo/v1, we monitor for specific system events or 'simulated' triggers
            if self._stranger_detected:
                self._lockdown()
                self._stranger_detected = False # Reset after lockdown
            
            time.sleep(2)

    def _lockdown(self):
        """Triggers the 'Aura' protective actions."""
        logger.warning("🚨 STRANGER DETECTED! Initiating Lockdown...")
        
        # Action A: Blur/Minimize sensitive apps
        # (Using system_control to minimize all windows)
        self.sys_ctrl.press_key("win+d")
        
        # Action B: Lock System as a safety fallback
        time.sleep(1)
        self.sys_ctrl.lock_system()

    def simulate_stranger(self):
        """Developer tool to test the lockdown."""
        self._stranger_detected = True
        return "Simulating stranger detection..."
