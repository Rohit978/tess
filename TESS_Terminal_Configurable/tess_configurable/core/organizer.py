"""
Organizer - File organization automation.
"""

import os
import shutil
from pathlib import Path
from typing import Dict, List
from datetime import datetime


class Organizer:
    """
    Organizes files based on criteria.
    """
    
    def __init__(self, brain=None):
        self.brain = brain
        
        # File type mappings
        self.type_map = {
            'images': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp'],
            'documents': ['.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt'],
            'spreadsheets': ['.xls', '.xlsx', '.csv', '.ods'],
            'presentations': ['.ppt', '.pptx', '.odp'],
            'archives': ['.zip', '.rar', '.7z', '.tar', '.gz'],
            'videos': ['.mp4', '.avi', '.mkv', '.mov', '.wmv'],
            'audio': ['.mp3', '.wav', '.flac', '.aac', '.ogg'],
            'code': ['.py', '.js', '.html', '.css', '.java', '.cpp', '.c', '.h'],
            'executables': ['.exe', '.msi', '.dmg', '.pkg', '.deb']
        }
    
    def organize(self, path: str, criteria: str = "type") -> str:
        """
        Organize files in a directory.
        
        Args:
            path: Directory to organize
            criteria: 'type', 'date', or 'size'
            
        Returns:
            Status message
        """
        source = Path(path)
        if not source.exists():
            return f"Path not found: {path}"
        
        if criteria == "type":
            return self._organize_by_type(source)
        elif criteria == "date":
            return self._organize_by_date(source)
        elif criteria == "size":
            return self._organize_by_size(source)
        else:
            return f"Unknown criteria: {criteria}"
    
    def _organize_by_type(self, source: Path) -> str:
        """Organize files by type."""
        moved = 0
        
        for file in source.iterdir():
            if file.is_file():
                ext = file.suffix.lower()
                
                # Find category
                category = 'others'
                for cat, exts in self.type_map.items():
                    if ext in exts:
                        category = cat
                        break
                
                # Create folder and move
                target_dir = source / category
                target_dir.mkdir(exist_ok=True)
                
                try:
                    shutil.move(str(file), str(target_dir / file.name))
                    moved += 1
                except Exception as e:
                    print(f"Error moving {file}: {e}")
        
        return f"Organized {moved} files by type"
    
    def _organize_by_date(self, source: Path) -> str:
        """Organize files by modification date."""
        moved = 0
        
        for file in source.iterdir():
            if file.is_file():
                # Get modification time
                mtime = datetime.fromtimestamp(file.stat().st_mtime)
                folder_name = mtime.strftime("%Y-%m")
                
                target_dir = source / folder_name
                target_dir.mkdir(exist_ok=True)
                
                try:
                    shutil.move(str(file), str(target_dir / file.name))
                    moved += 1
                except Exception as e:
                    print(f"Error moving {file}: {e}")
        
        return f"Organized {moved} files by date"
    
    def _organize_by_size(self, source: Path) -> str:
        """Organize files by size."""
        moved = 0
        
        size_categories = {
            'small': (0, 1024 * 1024),      # < 1MB
            'medium': (1024 * 1024, 100 * 1024 * 1024),  # 1MB - 100MB
            'large': (100 * 1024 * 1024, float('inf'))   # > 100MB
        }
        
        for file in source.iterdir():
            if file.is_file():
                size = file.stat().st_size
                
                # Find category
                category = 'others'
                for cat, (min_size, max_size) in size_categories.items():
                    if min_size <= size < max_size:
                        category = cat
                        break
                
                target_dir = source / category
                target_dir.mkdir(exist_ok=True)
                
                try:
                    shutil.move(str(file), str(target_dir / file.name))
                    moved += 1
                except Exception as e:
                    print(f"Error moving {file}: {e}")
        
        return f"Organized {moved} files by size"
    
    def clean_empty_folders(self, path: str) -> str:
        """Remove empty folders."""
        source = Path(path)
        removed = 0
        
        for folder in source.rglob('*'):
            if folder.is_dir() and not any(folder.iterdir()):
                try:
                    folder.rmdir()
                    removed += 1
                except:
                    pass
        
        return f"Removed {removed} empty folders"
