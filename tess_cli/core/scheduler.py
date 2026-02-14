import schedule
import threading
import time
import json
import os
from .logger import setup_logger

logger = setup_logger("Scheduler")

class TessScheduler:
    """
    Cron-like scheduler for TESS.
    Allows scheduling recurring tasks that TESS executes automatically.
    """
    def __init__(self, brain=None):
        self.brain = brain
        self.jobs = {}  # name -> {time, task, job_ref}
        self.running = False
        self.thread = None
        self.config_path = os.path.join(os.getcwd(), "config", "schedules.json")
        self._load_schedules()

    def _load_schedules(self):
        """Load saved schedules from disk."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    saved = json.load(f)
                for name, info in saved.items():
                    self.add_job(name, info['time'], info['task'], save=False)
                logger.info(f"Loaded {len(saved)} saved schedules.")
            except Exception as e:
                logger.error(f"Failed to load schedules: {e}")

    def _save_schedules(self):
        """Persist schedules to disk."""
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        data = {}
        for name, info in self.jobs.items():
            data[name] = {"time": info["time"], "task": info["task"]}
        with open(self.config_path, 'w') as f:
            json.dump(data, f, indent=2)

    def add_job(self, name, time_str, task_description, save=True):
        """
        Schedule a recurring daily task.
        
        Args:
            name: Unique job name (e.g., "morning_report")
            time_str: Time in HH:MM format (e.g., "08:00")
            task_description: Natural language task (e.g., "check my emails")
        """
        # Validate time format
        try:
            parts = time_str.split(":")
            int(parts[0])
            int(parts[1])
        except:
            return f"Invalid time format. Use HH:MM (e.g., 08:00)"

        # Cancel existing job with same name
        if name in self.jobs:
            self.remove_job(name)

        def job_callback():
            logger.info(f"⏰ Executing scheduled task: {name}")
            print(f"\n\n⏰ [SCHEDULER] Running: '{task_description}'")
            if self.brain:
                try:
                    response = self.brain.generate_command(task_description)
                    print(f"[SCHEDULER] Result: {response}")
                except Exception as e:
                    print(f"[SCHEDULER] Error: {e}")

        job_ref = schedule.every().day.at(time_str).do(job_callback)
        
        self.jobs[name] = {
            "time": time_str,
            "task": task_description,
            "job_ref": job_ref
        }
        
        if save:
            self._save_schedules()
        
        logger.info(f"Scheduled '{name}' at {time_str}: {task_description}")
        return f"✅ Scheduled '{name}' daily at {time_str}: \"{task_description}\""

    def remove_job(self, name):
        """Cancel a scheduled job."""
        if name not in self.jobs:
            return f"No schedule named '{name}' found."
        
        schedule.cancel_job(self.jobs[name]["job_ref"])
        del self.jobs[name]
        self._save_schedules()
        return f"🗑️ Cancelled schedule: {name}"

    def list_jobs(self):
        """List all active schedules."""
        if not self.jobs:
            return "No active schedules."
        
        lines = ["📋 Active Schedules:"]
        for name, info in self.jobs.items():
            lines.append(f"  • {name} → {info['time']} → \"{info['task']}\"")
        return "\n".join(lines)

    def start(self):
        """Start the scheduler background thread."""
        if self.running:
            return
            
        self.running = True
        
        def run_loop():
            while self.running:
                schedule.run_pending()
                time.sleep(30) # Check every 30 seconds
        
        self.thread = threading.Thread(target=run_loop, daemon=True)
        self.thread.start()
        logger.info("Scheduler started.")

    def stop(self):
        """Stop the scheduler."""
        self.running = False
