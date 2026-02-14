import os
from .logger import setup_logger

logger = setup_logger("FileManager")

class FileManager:
    """
    Handles file system operations: Reading, Writing, Listing, and Patching.
    """
    
    def list_dir(self, path="."):
        """
        Lists files and directories in the given path.
        """
        try:
            path = os.path.abspath(path)
            if not os.path.exists(path):
                return f"Error: Path '{path}' does not exist."
                
            items = os.listdir(path)
            # Differentiate files and folders
            files = []
            folders = []
            for item in items:
                if os.path.isdir(os.path.join(path, item)):
                    folders.append(item + "/")
                else:
                    files.append(item)
            
            return f"Directory: {path}\n\nFolders:\n" + "\n".join(folders) + "\n\nFiles:\n" + "\n".join(files)
        except Exception as e:
            logger.error(f"List dir error: {e}")
            return f"Error listing directory: {str(e)}"

    def read_file(self, path, max_lines=500):
        """
        Reads content of a file. Truncates if too large to prevent context overflow.
        """
        try:
            path = os.path.abspath(path)
            if not os.path.exists(path):
                return f"Error: File '{path}' does not exist."
            
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                
            total_lines = len(lines)
            content = "".join(lines[:max_lines])
            
            if total_lines > max_lines:
                content += f"\n\n... (File truncated. Showing {max_lines} of {total_lines} lines.)"
                
            return f"File: {path}\n\n{content}"
        except Exception as e:
            logger.error(f"Read file error: {e}")
            return f"Error reading file: {str(e)}"

    def write_file(self, path, content):
        """
        Writes (overwrites) content to a file. Creates if not exists.
        """
        try:
            path = os.path.abspath(path)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            return f"Successfully wrote to {path}"
        except Exception as e:
            logger.error(f"Write file error: {e}")
            return f"Error writing file: {str(e)}"

    def patch_file(self, path, search_text, replace_text):
        """
        Replaces specific text in a file.
        """
        try:
            path = os.path.abspath(path)
            if not os.path.exists(path):
                return f"Error: File '{path}' does not exist."
                
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            if search_text not in content:
                return "Error: Search text not found in file. Patch failed."
                
            new_content = content.replace(search_text, replace_text)
            
            with open(path, 'w', encoding='utf-8') as f:
                f.write(new_content)
                
            return f"Successfully patched {path}"
        except Exception as e:
            logger.error(f"Patch file error: {e}")
            return f"Error patching file: {str(e)}"
