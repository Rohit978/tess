"""
GSD Workspace Management for TESS

Implements spec-driven development methodologies inspired by 'Get Shit Done' (GSD).
Handles the creation, reading, and writing of PRD, Task, and Memory markdown files
to maintain explicit, externalized conceptual state for the LLM.
"""

import os
from datetime import datetime
from .logger import setup_logger

logger = setup_logger("GSDWorkspace")

class GSDWorkspace:
    def __init__(self, workspace_path):
        self.workspace_root = os.path.abspath(workspace_path)
        
    def init_workspace(self, project_name="TESS Project"):
        """Initializes a GSD workspace with standard spec files if they don't exist."""
        os.makedirs(self.workspace_root, exist_ok=True)
        
        files_created = []
        
        # 1. prd.md (Product Requirements Document)
        prd_path = os.path.join(self.workspace_root, "prd.md")
        if not os.path.exists(prd_path):
            with open(prd_path, "w", encoding="utf-8") as f:
                f.write(f"# Product Requirements Document: {project_name}\n\n")
                f.write("## Overview\nBrief description of the project goals.\n\n")
                f.write("## Requirements\n- Feature 1\n- Feature 2\n\n")
            files_created.append("prd.md")
            
        # 2. task.md (Step-by-step Execution Plan)
        task_path = os.path.join(self.workspace_root, "task.md")
        if not os.path.exists(task_path):
            with open(task_path, "w", encoding="utf-8") as f:
                f.write("# Task Execution Plan\n\n")
                f.write("## Phase 1: Initial Setup\n")
                f.write("- [ ] Create boilerplate\n")
                f.write("- [ ] Setup dependencies\n")
            files_created.append("task.md")
            
        # 3. memory.md (Learnings and Context)
        memory_path = os.path.join(self.workspace_root, "memory.md")
        if not os.path.exists(memory_path):
            with open(memory_path, "w", encoding="utf-8") as f:
                f.write("# Project Memory\n\n")
                f.write(f"*Workspace initialized at: {datetime.now().isoformat()}*\n\n")
                f.write("## Key Learnings\n- Record architectural decisions here.\n\n")
                f.write("## API Keys / Environment Info\n- Required environment variables.\n")
            files_created.append("memory.md")
            
        if files_created:
            logger.info(f"GSD Workspace initialized at {self.workspace_root}. Created: {', '.join(files_created)}")
            return f"Initialized GSD specs in {self.workspace_root}: {', '.join(files_created)}"
        else:
            return "GSD Workspace already initialized (spec files exist)."

    def get_state(self):
        """Reads all GSD spec files and returns them as a single concatenated string for LLM context."""
        state = ""
        files_to_read = ["prd.md", "memory.md", "task.md"] # Read in dependency order
        
        for filename in files_to_read:
            filepath = os.path.join(self.workspace_root, filename)
            if os.path.exists(filepath):
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        content = f.read()
                        state += f"\n\n--- Start of {filename} ---\n{content}\n--- End of {filename} ---\n"
                except Exception as e:
                    logger.error(f"Failed to read {filename}: {e}")
                    
        return state.strip()

    def update_task_status(self, task_description, completed=True):
        """Helper function to programmatically check off a task in task.md"""
        task_path = os.path.join(self.workspace_root, "task.md")
        if not os.path.exists(task_path):
            return "Error: task.md not found."
            
        try:
            with open(task_path, "r", encoding="utf-8") as f:
                content = f.read()
                
            # Naive replacement for checkmarks
            if completed:
                new_content = content.replace(f"- [ ] {task_description}", f"- [x] {task_description}")
            else:
                 new_content = content.replace(f"- [x] {task_description}", f"- [ ] {task_description}")
                 
            if content != new_content:     
                with open(task_path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                return f"Task '{task_description}' marked as {'completed' if completed else 'pending'}."
            return "Task not found to update."
        except Exception as e:
            logger.error(f"Failed to update task.md: {e}")
            return f"Error updating task: {e}"
