"""
Task Registry - Manage background tasks.
"""

import threading
import uuid
from typing import Dict, List, Callable, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Task:
    """Represents a running task."""
    id: str
    name: str
    thread: threading.Thread
    stop_event: threading.Event
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    status: str = "running"


class TaskRegistry:
    """
    Manages background tasks with start/stop capabilities.
    """
    
    def __init__(self):
        self.tasks: Dict[str, Task] = {}
    
    def start_task(self, name: str, target: Callable, args: tuple = ()) -> str:
        """
        Start a new background task.
        
        Args:
            name: Task name
            target: Function to run
            args: Arguments for function
            
        Returns:
            Task ID
        """
        task_id = str(uuid.uuid4())[:8]
        stop_event = threading.Event()
        
        # Wrap target to check stop_event
        def wrapper():
            try:
                if 'stop_event' in target.__code__.co_varnames:
                    target(*args, stop_event=stop_event)
                else:
                    target(*args)
            except Exception as e:
                print(f"Task {name} error: {e}")
        
        thread = threading.Thread(target=wrapper, daemon=True)
        thread.start()
        
        task = Task(
            id=task_id,
            name=name,
            thread=thread,
            stop_event=stop_event
        )
        
        self.tasks[task_id] = task
        return task_id
    
    def stop_task(self, task_id: str) -> str:
        """
        Stop a task by ID.
        
        Args:
            task_id: Task ID to stop
            
        Returns:
            Status message
        """
        task = self.tasks.get(task_id)
        if not task:
            return f"Task {task_id} not found"
        
        task.stop_event.set()
        task.status = "stopping"
        
        # Wait a bit for graceful shutdown
        task.thread.join(timeout=2)
        
        if task.thread.is_alive():
            task.status = "force_stopped"
        else:
            task.status = "stopped"
        
        del self.tasks[task_id]
        return f"Stopped task {task.name} ({task_id})"
    
    def list_tasks(self) -> str:
        """
        List all active tasks.
        
        Returns:
            Formatted task list
        """
        if not self.tasks:
            return "No active tasks"
        
        lines = ["Active Tasks:", "-" * 40]
        for tid, task in self.tasks.items():
            alive = "✓" if task.thread.is_alive() else "✗"
            lines.append(f"[{alive}] {tid}: {task.name} ({task.status})")
        
        return "\n".join(lines)
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID."""
        return self.tasks.get(task_id)
    
    def stop_all(self):
        """Stop all tasks."""
        for tid in list(self.tasks.keys()):
            self.stop_task(tid)
