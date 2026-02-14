"""
Workflow Engine - Automated task sequences and routines.
"""

import json
import schedule
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, asdict


@dataclass
class WorkflowStep:
    """Single step in a workflow."""
    action: str
    params: Dict[str, Any]
    condition: Optional[str] = None  # Optional condition to execute
    delay: int = 0  # Delay in seconds before next step


@dataclass
class Workflow:
    """A complete workflow definition."""
    name: str
    description: str
    trigger_type: str  # 'schedule', 'event', 'manual'
    trigger_config: Dict[str, Any]  # schedule time, event conditions, etc.
    steps: List[WorkflowStep]
    enabled: bool = True
    last_run: Optional[str] = None
    run_count: int = 0
    created_at: str = ""
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


class WorkflowEngine:
    """
    Manages and executes automated workflows.
    
    Examples:
    - Morning routine: Open apps, check email
    - Cleanup routine: Organize downloads, clear temp files
    - Meeting prep: Open calendar, prepare notes
    """
    
    def __init__(self, brain=None, orchestrator=None):
        self.brain = brain
        self.orchestrator = orchestrator
        
        from ..config_manager import get_config_manager
        config = get_config_manager()
        self.workflows_dir = Path(config.config.paths.data_dir) / "workflows"
        self.workflows_dir.mkdir(parents=True, exist_ok=True)
        
        self.workflows: Dict[str, Workflow] = {}
        self.running = False
        self.scheduler_thread: Optional[threading.Thread] = None
        
        self._load_workflows()
        self._start_scheduler()
    
    def _load_workflows(self):
        """Load saved workflows from disk."""
        for file in self.workflows_dir.glob("*.json"):
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                # Convert dict back to Workflow
                steps = [WorkflowStep(**s) for s in data.pop('steps', [])]
                self.workflows[data['name']] = Workflow(steps=steps, **data)
                
            except Exception as e:
                print(f"Error loading workflow {file}: {e}")
    
    def _save_workflow(self, workflow: Workflow):
        """Save a workflow to disk."""
        file_path = self.workflows_dir / f"{workflow.name.replace(' ', '_')}.json"
        
        data = asdict(workflow)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    
    def create_workflow(self, name: str, description: str, 
                       trigger_type: str, trigger_config: Dict,
                       steps: List[WorkflowStep]) -> Workflow:
        """
        Create a new workflow.
        
        Args:
            name: Workflow name
            description: What it does
            trigger_type: 'schedule', 'event', or 'manual'
            trigger_config: Trigger configuration
            steps: List of workflow steps
            
        Returns:
            Created workflow
        """
        workflow = Workflow(
            name=name,
            description=description,
            trigger_type=trigger_type,
            trigger_config=trigger_config,
            steps=steps
        )
        
        self.workflows[name] = workflow
        self._save_workflow(workflow)
        
        # Register schedule if needed
        if trigger_type == 'schedule':
            self._register_schedule(workflow)
        
        return workflow
    
    def _register_schedule(self, workflow: Workflow):
        """Register a scheduled workflow."""
        config = workflow.trigger_config
        time_str = config.get('time', '09:00')
        days = config.get('days', ['monday', 'tuesday', 'wednesday', 'thursday', 'friday'])
        
        job_func = lambda: self._execute_workflow(workflow.name)
        
        for day in days:
            if day == 'monday':
                schedule.every().monday.at(time_str).do(job_func)
            elif day == 'tuesday':
                schedule.every().tuesday.at(time_str).do(job_func)
            elif day == 'wednesday':
                schedule.every().wednesday.at(time_str).do(job_func)
            elif day == 'thursday':
                schedule.every().thursday.at(time_str).do(job_func)
            elif day == 'friday':
                schedule.every().friday.at(time_str).do(job_func)
            elif day == 'saturday':
                schedule.every().saturday.at(time_str).do(job_func)
            elif day == 'sunday':
                schedule.every().sunday.at(time_str).do(job_func)
            elif day == 'daily':
                schedule.every().day.at(time_str).do(job_func)
    
    def _start_scheduler(self):
        """Start the background scheduler."""
        if self.running:
            return
        
        self.running = True
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.scheduler_thread.start()
    
    def _scheduler_loop(self):
        """Main scheduler loop."""
        while self.running:
            schedule.run_pending()
            time.sleep(1)
    
    def _execute_workflow(self, workflow_name: str, output_callback=None) -> str:
        """
        Execute a workflow.
        
        Args:
            workflow_name: Name of workflow to run
            output_callback: Optional callback for output
            
        Returns:
            Execution result
        """
        workflow = self.workflows.get(workflow_name)
        if not workflow:
            return f"Workflow '{workflow_name}' not found"
        
        if not workflow.enabled:
            return f"Workflow '{workflow_name}' is disabled"
        
        if output_callback:
            output_callback(f"\n[WORKFLOW] Starting: {workflow.name}")
            output_callback(f"[WORKFLOW] {workflow.description}\n")
        
        results = []
        
        for i, step in enumerate(workflow.steps, 1):
            if output_callback:
                output_callback(f"[Step {i}/{len(workflow.steps)}] {step.action}")
            
            # Check condition if present
            if step.condition and not self._evaluate_condition(step.condition):
                if output_callback:
                    output_callback("  [SKIP] Condition not met")
                continue
            
            # Execute step
            try:
                result = self._execute_step(step)
                results.append(result)
                
                if output_callback:
                    output_callback(f"  [OK] {result[:100]}...")
                
            except Exception as e:
                error_msg = f"Error: {e}"
                results.append(error_msg)
                if output_callback:
                    output_callback(f"  [ERROR] {error_msg}")
            
            # Delay before next step
            if step.delay > 0:
                time.sleep(step.delay)
        
        # Update workflow stats
        workflow.last_run = datetime.now().isoformat()
        workflow.run_count += 1
        self._save_workflow(workflow)
        
        return f"Workflow completed: {len(results)} steps executed"
    
    def _execute_step(self, step: WorkflowStep) -> str:
        """Execute a single workflow step."""
        action = step.action.lower()
        params = step.params
        
        if action == 'launch_app':
            app = params.get('app', 'notepad')
            # Use system command
            import subprocess
            subprocess.Popen(app, shell=True)
            return f"Launched {app}"
        
        elif action == 'open_url':
            url = params.get('url', 'https://google.com')
            import webbrowser
            webbrowser.open(url)
            return f"Opened {url}"
        
        elif action == 'execute_command':
            cmd = params.get('command', '')
            import subprocess
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            return result.stdout[:200]
        
        elif action == 'send_notification':
            title = params.get('title', 'TESS')
            message = params.get('message', '')
            # Simple notification (platform-specific)
            try:
                if os.name == 'nt':  # Windows
                    import ctypes
                    ctypes.windll.user32.MessageBoxW(0, message, title, 0x40)
                else:  # Mac/Linux
                    subprocess.run(['notify-send', title, message])
            except:
                pass
            return f"Notification: {message}"
        
        elif action == 'wait':
            seconds = params.get('seconds', 1)
            time.sleep(seconds)
            return f"Waited {seconds}s"
        
        elif action == 'ai_prompt':
            prompt = params.get('prompt', '')
            if self.brain:
                response = self.brain.think(prompt)
                return response or "No response"
            return "Brain not available"
        
        else:
            return f"Unknown action: {action}"
    
    def _evaluate_condition(self, condition: str) -> bool:
        """Evaluate a condition string."""
        # Simple condition evaluation
        # TODO: Make this more sophisticated
        if "time" in condition:
            # Check time-based condition
            return True
        return True
    
    def list_workflows(self) -> str:
        """List all workflows."""
        if not self.workflows:
            return "No workflows defined"
        
        lines = ["Workflows:", "-" * 50]
        
        for name, wf in self.workflows.items():
            status = "✓" if wf.enabled else "✗"
            trigger = f"{wf.trigger_type} {wf.trigger_config.get('time', '')}"
            lines.append(f"[{status}] {name}: {trigger}")
            lines.append(f"    {wf.description}")
            if wf.last_run:
                lines.append(f"    Last run: {wf.last_run[:16]}")
        
        return "\n".join(lines)
    
    def run_workflow(self, name: str, output_callback=None) -> str:
        """Manually trigger a workflow."""
        return self._execute_workflow(name, output_callback)
    
    def delete_workflow(self, name: str) -> bool:
        """Delete a workflow."""
        if name not in self.workflows:
            return False
        
        # Remove file
        file_path = self.workflows_dir / f"{name.replace(' ', '_')}.json"
        if file_path.exists():
            file_path.unlink()
        
        # Remove from memory
        del self.workflows[name]
        return True
    
    def toggle_workflow(self, name: str) -> bool:
        """Enable/disable a workflow."""
        if name not in self.workflows:
            return False
        
        self.workflows[name].enabled = not self.workflows[name].enabled
        self._save_workflow(self.workflows[name])
        return self.workflows[name].enabled
    
    def create_preset_workflow(self, preset_name: str) -> Optional[Workflow]:
        """Create a preset workflow."""
        presets = {
            "morning_routine": {
                "description": "Start the day with essential apps and info",
                "trigger_type": "schedule",
                "trigger_config": {"time": "09:00", "days": ["monday", "tuesday", "wednesday", "thursday", "friday"]},
                "steps": [
                    WorkflowStep("open_url", {"url": "https://calendar.google.com"}, delay=2),
                    WorkflowStep("open_url", {"url": "https://mail.google.com"}, delay=2),
                    WorkflowStep("launch_app", {"app": "notepad"}),
                    WorkflowStep("send_notification", {"title": "Good Morning!", "message": "Your morning routine is ready"}),
                ]
            },
            "focus_mode": {
                "description": "Minimize distractions for deep work",
                "trigger_type": "manual",
                "trigger_config": {},
                "steps": [
                    WorkflowStep("send_notification", {"title": "Focus Mode", "message": "Starting focus session. Notifications muted."}),
                    WorkflowStep("launch_app", {"app": "notepad"}),
                ]
            },
            "cleanup_downloads": {
                "description": "Organize downloads folder",
                "trigger_type": "schedule",
                "trigger_config": {"time": "18:00", "days": ["daily"]},
                "steps": [
                    WorkflowStep("send_notification", {"title": "Cleanup", "message": "Organizing downloads folder..."}),
                ]
            },
        }
        
        if preset_name not in presets:
            return None
        
        preset = presets[preset_name]
        return self.create_workflow(
            name=preset_name,
            description=preset["description"],
            trigger_type=preset["trigger_type"],
            trigger_config=preset["trigger_config"],
            steps=preset["steps"]
        )
