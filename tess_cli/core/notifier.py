import logging
import threading

logger = logging.getLogger("Notifier")

class Notifier:
    """
    Handles desktop notifications for TESS.
    Uses win11toast for native Windows 11/10 integration.
    """
    
    @staticmethod
    def notify(title, message, duration="short"):
        """
        Sends a desktop notification.
        Run in a separate thread to avoid blocking.
        """
        threading.Thread(target=Notifier._send, args=(title, message, duration), daemon=True).start()

    @staticmethod
    def _send(title, message, duration):
        try:
            from win11toast import toast
            # duration map: short -> default, long -> duration='long'
            # win11toast supports 'duration'='short'|'long'
            
            # Use TESS icon if available (future), for now default
            toast(title, message, duration=duration, networking={"app_id": "TESS Terminal Pro"})
            
        except ImportError:
            logger.debug("win11toast not installed. Notifications disabled.")
        except Exception as e:
            logger.debug(f"Failed to send notification: {e}")
