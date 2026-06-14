import os
import time
import threading
from datetime import datetime
from .logger import setup_logger
from .os_controller import OSController
from .desktop_vision import DesktopVisionController

logger = setup_logger("VisualTimeline")

class VisualTimelineTracker:
    """
    Background worker that periodically snapshots desktop context (active app, window title, 
    and visible text content) and indexes them into ChromaDB for temporal RAG queries.
    Incurs zero API token costs by querying local Windows UI Automation (UIA) tree.
    """
    def __init__(self, brain, knowledge_db, interval_sec=60):
        self.brain = brain
        self.knowledge_db = knowledge_db
        self.interval_sec = interval_sec
        self.running = False
        self.thread = None
        self.os_ctrl = OSController(brain=brain)
        self.last_screen_text = ""

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True, name="VisualTimelineTracker")
        self.thread.start()
        logger.info("Visual Timeline Tracker started.")

    def stop(self):
        self.running = False
        logger.info("Visual Timeline Tracker stopped.")

    def _run_loop(self):
        while self.running:
            try:
                # 1. Get active app title
                dv = DesktopVisionController()
                active = dv.active_app()
                
                # 2. Extract visible texts from the active window UIA tree (fast and free)
                screen_text = ""
                window = self.os_ctrl._get_window()
                if window:
                    try:
                        texts = []
                        for ctrl in window.descendants():
                            t = ctrl.window_text().strip()
                            if t and len(t) > 1:
                                texts.append(t)
                        # Remove duplicates while keeping order
                        screen_text = " | ".join(dict.fromkeys(texts))[:1000]
                    except:
                        pass
                
                # 3. Index screen state if there is a context change
                if screen_text and screen_text != self.last_screen_text:
                    self.last_screen_text = screen_text
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    log_entry = f"Screen View at {timestamp} | Active Window: {active} | Content: {screen_text}"
                    
                    if self.knowledge_db:
                        self.knowledge_db.store_memory(
                            log_entry,
                            metadata={"type": "screen_snapshot", "timestamp": timestamp, "active_window": active}
                        )
                        logger.info("Indexed new visual timeline event.")
            except Exception as e:
                logger.error(f"Visual Timeline loop error: {e}")
                
            time.sleep(self.interval_sec)
