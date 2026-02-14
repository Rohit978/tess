import time
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from .logger import setup_logger
from .config import Config

logger = setup_logger("Librarian")

class LibrarianHandler(FileSystemEventHandler):
    """
    Handles file system events and triggers learning.
    """
    def __init__(self, knowledge_db):
        self.kb = knowledge_db
        self.last_learning = {} # Debounce map: file_path -> timestamp

    def on_modified(self, event):
        if event.is_directory:
            return
            
        # Filter for text/code files
        valid_exts = {'.py', '.js', '.html', '.css', '.md', '.txt', '.json', '.java', '.c', '.cpp', '.h', '.ps1'}
        ext = os.path.splitext(event.src_path)[1].lower()
        
        if ext not in valid_exts:
            return

        # Debounce (prevent double-firing on some editors)
        now = time.time()
        last = self.last_learning.get(event.src_path, 0)
        if now - last < 2.0: # 2 seconds cooldown
            return
            
        self.last_learning[event.src_path] = now
        logger.info(f"Detected change in: {os.path.basename(event.src_path)}")
        
        try:
            # Read content
            with open(event.src_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
            if not content.strip(): return

            # Update Knowledge Base (RAG)
            doc_id = f"file_{event.src_path}"
            
            # Upsert into ChromaDB
            # Upsert into ChromaDB
            chunks = self.kb._chunk_text(content, max_chars=1500, overlap=150)
            
            ids = [f"{doc_id}_{i}" for i in range(len(chunks))]
            metadatas = [{"source": event.src_path, "type": "code_file", "timestamp": str(now), "chunk_index": i} for i in range(len(chunks))]

            self.kb.collection.upsert(
                documents=chunks,
                metadatas=metadatas,
                ids=ids
            )
            logger.info(f"Librarian learned: {os.path.basename(event.src_path)}")
            
        except Exception as e:
            logger.error(f"Librarian failed to learn {event.src_path}: {e}")

class Librarian:
    """
    Background service that watches the project directory and keeps TESS updated.
    """
    def __init__(self, knowledge_base, watch_path=None):
        self.kb = knowledge_base
        self.watch_path = watch_path or os.getcwd()
        self.observer = Observer()
        self.handler = LibrarianHandler(self.kb)

    def start(self):
        """Starts the background watcher thread."""
        logger.info(f"Librarian starting watch on: {self.watch_path}")
        self.observer.schedule(self.handler, self.watch_path, recursive=True)
        self.observer.start()
        
    def stop(self):
        """Stops the watcher."""
        if self.observer.is_alive():
            self.observer.stop()
            self.observer.join()

    def change_watch_path(self, new_path):
        """Switches the directory being watched."""
        if not os.path.exists(new_path):
            return False, "Path does not exist."
            
        self.stop()
        
        self.watch_path = new_path
        self.observer = Observer() # Re-init observer
        self.observer.schedule(self.handler, self.watch_path, recursive=True)
        self.observer.start()
        
        logger.info(f"Librarian switched to: {new_path}")
        return True, f"Now watching: {new_path}"
