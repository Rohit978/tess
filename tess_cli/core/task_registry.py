import threading
import time
from .logger import setup_logger

logger = setup_logger("TaskRegistry")

class TaskRegistry:
    """
    Manages background tasks (threads) to allow User to List/Kill them.
    """
    def __init__(self):
        self.tasks = {} # id -> {"name": str, "thread": Thread, "stop_event": Event}
        self.lock = threading.Lock()
        
    def start_task(self, name, target, args=()):
        """
        Starts a new task in a background thread.
        'target' function must accept 'stop_event' as its first argument.
        """
        with self.lock:
            task_id = str(len(self.tasks) + 1)
            stop_event = threading.Event()
            
            # wrapper to clean up registry when done
            def wrapper():
                try:
                    target(stop_event, *args)
                except Exception as e:
                    logger.error(f"Task '{name}' failed: {e}")
                finally:
                    self._remove_task(task_id)
            
            t = threading.Thread(target=wrapper, daemon=True, name=name)
            t.start()
            
            self.tasks[task_id] = {
                "name": name,
                "thread": t,
                "stop_event": stop_event,
                "start_time": time.time()
            }
            logger.info(f"Started task {task_id}: {name}")
            return task_id
            
    def _remove_task(self, task_id):
        with self.lock:
            if task_id in self.tasks:
                del self.tasks[task_id]

    def stop_task(self, task_id):
        with self.lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                logger.info(f"Stopping task {task_id}: {task['name']}")
                task["stop_event"].set()
                return f"Signal sent to stop task {task_id}: {task['name']}"
            return f"Task ID {task_id} not found."

    def list_tasks(self):
        with self.lock:
            if not self.tasks:
                return "No background tasks running."
            
            report = "running_tasks:\n"
            for tid, task in self.tasks.items():
                duration = int(time.time() - task["start_time"])
                report += f"  - ID: {tid} | Name: {task['name']} | Uptime: {duration}s\n"
            return report
