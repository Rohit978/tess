"""
Scheduler - Time-based task scheduling.
"""

import schedule
import threading
import time
from typing import Dict, Callable, Optional
from dataclasses import dataclass


@dataclass
class ScheduledJob:
    """Represents a scheduled job."""
    name: str
    time: str
    task: str
    job = None


class TessScheduler:
    """
    Schedules tasks to run at specific times.
    """
    
    def __init__(self, brain=None):
        self.brain = brain
        self.jobs: Dict[str, ScheduledJob] = {}
        self.running = False
        self.thread: Optional[threading.Thread] = None
    
    def start(self):
        """Start the scheduler loop."""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
    
    def _run_loop(self):
        """Main scheduler loop."""
        while self.running:
            schedule.run_pending()
            time.sleep(1)
    
    def stop(self):
        """Stop the scheduler."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
    
    def add_job(self, name: str, time_str: str, task_desc: str) -> str:
        """
        Add a scheduled job.
        
        Args:
            name: Job name
            time_str: Time in HH:MM format
            task_desc: Task description to execute
            
        Returns:
            Status message
        """
        try:
            # Parse time
            hour, minute = map(int, time_str.split(':'))
            
            # Create job function
            def job_func():
                print(f"\n[SCHEDULER] Running scheduled task: {task_desc}")
                if self.brain:
                    # TODO: Execute through brain
                    print(f"Would execute: {task_desc}")
            
            # Schedule it
            job = schedule.every().day.at(time_str).do(job_func)
            
            scheduled = ScheduledJob(name, time_str, task_desc)
            scheduled.job = job
            self.jobs[name] = scheduled
            
            return f"Scheduled '{name}' at {time_str}"
            
        except Exception as e:
            return f"Scheduling error: {e}"
    
    def remove_job(self, name: str) -> str:
        """Remove a scheduled job."""
        job = self.jobs.get(name)
        if not job:
            return f"Job '{name}' not found"
        
        if job.job:
            schedule.cancel_job(job.job)
        
        del self.jobs[name]
        return f"Removed job '{name}'"
    
    def list_jobs(self) -> str:
        """List all scheduled jobs."""
        if not self.jobs:
            return "No scheduled jobs"
        
        lines = ["Scheduled Jobs:", "-" * 40]
        for name, job in self.jobs.items():
            lines.append(f"• {name}: {job.time} - {job.task}")
        
        return "\n".join(lines)
    
    def clear_all(self):
        """Clear all jobs."""
        schedule.clear()
        self.jobs.clear()
