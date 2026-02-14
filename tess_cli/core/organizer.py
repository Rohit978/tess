import os
import shutil
import logging
import json
import time

logger = logging.getLogger("Organizer")

class Organizer:
    """
    Intelligent File Organizer using LLM for categorization.
    """
    def __init__(self, brain):
        self.brain = brain

    def organize(self, path, criteria="general_cleanup"):
        """
        Scans a directory and organizes files based on criteria.
        """
        if path == "." or path == "./":
            path = os.getcwd()
            
        if not os.path.exists(path):
            return f"Path not found: {path}"
            
        logger.info(f"Scanning {path} for organization (Criteria: {criteria})...")
        
        # 1. Gather Files (Ignore folders to be safe)
        try:
            all_items = os.listdir(path)
        except Exception as e:
             return f"Error listing directory: {e}"
             
        files = [f for f in all_items if os.path.isfile(os.path.join(path, f)) and not f.startswith('.')]
        
        # Filter out script files to prevent self-organizing the brain
        files = [f for f in files if f not in ["main.py", "run_terminal_tess.py"]]
        
        if not files:
            return "No files found to organize."
        
        print(f"Found {len(files)} files to organize.")
        
        # 2. Ask Brain to Categorize in Batches
        batch_size = 20
        all_moves = {}
        
        for i in range(0, len(files), batch_size):
            batch = files[i:i+batch_size]
            print(f"Categorizing batch {i//batch_size + 1}...")
            
            prompt = f"""
            Task: Categorize these files based on criteria: "{criteria}".
            
            Files:
            {json.dumps(batch)}
            
            Instructions:
            - Create LOGICAL folder names (e.g., "Images", "Invoices", "Python_Scripts", "Tess_Project").
            - If criteria is specific (e.g. "Project X"), group relevant files there and others in "Misc" or "Other".
            - Return JSON: {{ "filename": "FolderName", ... }}
            - Use "null" if file should NOT be moved.
            """
            
            system_prompt = "You are an intelligent file organizer. Output purely JSON."
            
            try:
                response_text = self.brain.think(prompt, system_prompt)
                if response_text:
                    # Parse JSON
                    batch_moves = json.loads(response_text)
                    all_moves.update(batch_moves)
                time.sleep(1) # Rate limit nice-ness
            except Exception as e:
                logger.error(f"Batch categorization failed: {e}")
                
        # 3. Execute Moves
        return self.execute_moves(path, all_moves)

    def execute_moves(self, base_path, moves):
        results = []
        moved_count = 0
        
        for filename, folder in moves.items():
            if not folder or folder.lower() == "null" or folder == "":
                continue
                
            # Create target folder
            target_dir = os.path.join(base_path, folder)
            if not os.path.exists(target_dir):
                try:
                    os.makedirs(target_dir)
                except OSError:
                    continue # Valid folder name issue?
            
            src = os.path.join(base_path, filename)
            dst = os.path.join(target_dir, filename)
            
            # Don't overwrite
            if os.path.exists(dst):
                base, ext = os.path.splitext(filename)
                dst = os.path.join(target_dir, f"{base}_{int(time.time())}{ext}")
            
            try:
                # Sanity check: src exists
                if os.path.exists(src):
                    shutil.move(src, dst)
                    results.append(f"Moved {filename} -> {folder}/")
                    moved_count += 1
            except Exception as e:
                results.append(f"Failed to move {filename}: {e}")
        
        summary = f"Organization Complete. Moved {moved_count} files.\n"
        if moved_count > 0:
            summary += "\n".join(results[:5]) # Show first 5
            if len(results) > 5: summary += f"\n...and {len(results)-5} more."
        else:
            summary += "No files needed moving."
            
        return summary
