import json
import os
import time
from datetime import datetime
from .logger import setup_logger

logger = setup_logger("MemoryEngine")

class MemoryEngine:
    """
    A lightweight, persistent memory system for TESS.
    Stores memories in a JSON file and supports basic semantic retrieval (keyword/context).
    """
    
    def __init__(self, user_id="default"):
        self.user_id = user_id
        self.memory_dir = os.path.join(os.getcwd(), "tess_memory")
        self.memory_file = os.path.join(self.memory_dir, f"{user_id}_memory.json")
        self._ensure_memory_file()
        self.memories = self._load_memory()

    def _ensure_memory_file(self):
        if not os.path.exists(self.memory_dir):
            os.makedirs(self.memory_dir)
        if not os.path.exists(self.memory_file):
            with open(self.memory_file, 'w') as f:
                json.dump([], f)

    def _load_memory(self):
        try:
            with open(self.memory_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load memory: {e}")
            return []

    def _save_memory(self):
        try:
            with open(self.memory_file, 'w') as f:
                json.dump(self.memories, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save memory: {e}")

    def store_memory(self, text, metadata=None):
        """
        Saves a new memory fragment.
        """
        entry = {
            "id": str(int(time.time() * 1000)),
            "timestamp": datetime.now().isoformat(),
            "text": text,
            "metadata": metadata or {}
        }
        self.memories.append(entry)
        self._save_memory()
        logger.info(f"Memory stored: {text[:50]}...")
        return entry["id"]

    def add_thought(self, text):
        """Robustness alias for context distillation."""
        return self.store_memory(text)

    def retrieve_context(self, query, limit=3):
        """
        Retrieves relevant memories based on keyword overlap (TF-IDF style simplified).
        TODO: Upgrade to Vector Embeddings (ChromaDB/FAISS) for true semantic search.
        """
        query_words = set(query.lower().split())
        scored_memories = []

        for mem in self.memories:
            mem_words = set(mem["text"].lower().split())
            # Jaccard similarity (intersection over union)
            intersection = query_words.intersection(mem_words)
            if not intersection:
                continue
            
            score = len(intersection) / len(query_words.union(mem_words))
            scored_memories.append((score, mem))

        # Sort by score descending
        scored_memories.sort(key=lambda x: x[0], reverse=True)
        
        # Return top N text chunks
        return [m[1]["text"] for m in scored_memories[:limit]]

    def memorize(self, text):
        """
        Explicit command to memorize something.
        """
        self.store_memory(text, metadata={"type": "explicit_instruction"})
        return f"I have memorized: '{text}'"
