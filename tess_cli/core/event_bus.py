import logging
import threading
import queue
from typing import Callable, Any, Dict, List

logger = logging.getLogger("TessEventBus")

class TessEventBus:
    """
    Asynchronous, thread-safe Event Bus for TESS Event-Driven Cognition.
    Allows decoupling of different sub-brains and reactive modules.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(TessEventBus, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized") and self._initialized:
            return
        
        self.listeners: Dict[str, List[Callable[[Any], None]]] = {}
        self.event_queue = queue.Queue()
        self.worker_thread = None
        self.running = False
        self.listener_lock = threading.Lock()
        self._initialized = True
        self.start()

    def start(self):
        """Starts the background event processor."""
        if self.running:
            return
        self.running = True
        self.worker_thread = threading.Thread(target=self._process_events, daemon=True, name="TessEventBusWorker")
        self.worker_thread.start()
        logger.info("Event Bus started successfully.")

    def stop(self):
        """Stops the event processor."""
        self.running = False
        self.event_queue.put((None, None))  # Poison pill
        if self.worker_thread:
            self.worker_thread.join(timeout=1.0)
        logger.info("Event Bus stopped.")

    def subscribe(self, event_type: str, callback: Callable[[Any], None]):
        """Subscribe a listener to a specific event type."""
        with self.listener_lock:
            if event_type not in self.listeners:
                self.listeners[event_type] = []
            if callback not in self.listeners[event_type]:
                self.listeners[event_type].append(callback)
                logger.debug(f"Subscribed {callback.__name__ if hasattr(callback, '__name__') else str(callback)} to {event_type}")

    def unsubscribe(self, event_type: str, callback: Callable[[Any], None]):
        """Unsubscribe a listener from an event type."""
        with self.listener_lock:
            if event_type in self.listeners and callback in self.listeners[event_type]:
                self.listeners[event_type].remove(callback)
                logger.debug(f"Unsubscribed from {event_type}")

    def publish(self, event_type: str, data: Any):
        """Publish an event asynchronously."""
        if not self.running:
            self.start()
        self.event_queue.put((event_type, data))

    def publish_sync(self, event_type: str, data: Any):
        """Publish an event and invoke all subscribers synchronously."""
        with self.listener_lock:
            callbacks = list(self.listeners.get(event_type, []))
            
        for callback in callbacks:
            try:
                callback(data)
            except Exception as e:
                logger.error(f"Error in synchronous subscriber for event '{event_type}': {e}", exc_info=True)

    def _process_events(self):
        """Background loop to route events from the queue to subscribers."""
        while True:
            try:
                event_type, data = self.event_queue.get(timeout=0.5)
                if event_type is None:  # Poison pill — only reliable exit
                    break
                
                with self.listener_lock:
                    callbacks = list(self.listeners.get(event_type, []))
                
                for callback in callbacks:
                    try:
                        callback(data)
                    except Exception as e:
                        logger.error(f"Error in event subscriber for event '{event_type}': {e}", exc_info=True)
                
                self.event_queue.task_done()
            except queue.Empty:
                if not self.running:  # Only check flag during idle periods
                    break
                continue
            except Exception as e:
                logger.error(f"Event Bus worker encountered an error: {e}", exc_info=True)

# Helper singleton instance
event_bus = TessEventBus()
