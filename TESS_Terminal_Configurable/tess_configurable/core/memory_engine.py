"""
Memory Engine for TESS - Persistent memory storage.
"""

import json
import os
import time
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path


class MemoryEngine:
    """
    Lightweight persistent memory system.
    Stores memories as JSON for easy retrieval.
    """
    
    def __init__(self, user_id: str = "default", memory_dir: Optional[str] = None):
        self.user_id = user_id
        
        if memory_dir is None:
            from ..config_manager import get_config_manager
            config = get_config_manager()
            memory_dir = config.config.paths.memory_dir
        
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        
        self.memory_file = self.memory_dir / f"{user_id}_memory.json"
        self.memories: List[Dict] = []
        self._load()
    
    def _load(self):
        """Load memories from file."""
        if self.memory_file.exists():
            try:
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    self.memories = json.load(f)
            except Exception as e:
                print(f"Error loading memory: {e}")
                self.memories = []
    
    def _save(self):
        """Save memories to file."""
        try:
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                json.dump(self.memories, f, indent=2)
        except Exception as e:
            print(f"Error saving memory: {e}")
    
    def store(self, text: str, metadata: Optional[Dict] = None) -> str:
        """
        Store a memory.
        
        Args:
            text: Content to remember
            metadata: Optional metadata dict
            
        Returns:
            Memory ID
        """
        entry = {
            "id": str(int(time.time() * 1000)),
            "timestamp": datetime.now().isoformat(),
            "text": text,
            "metadata": metadata or {}
        }
        
        self.memories.append(entry)
        self._save()
        return entry["id"]
    
    def retrieve(self, query: str, limit: int = 3) -> List[str]:
        """
        Retrieve relevant memories based on keyword matching.
        
        Args:
            query: Search query
            limit: Max results to return
            
        Returns:
            List of memory texts
        """
        query_words = set(query.lower().split())
        scored = []
        
        for mem in self.memories:
            mem_words = set(mem["text"].lower().split())
            intersection = query_words.intersection(mem_words)
            
            if intersection:
                # Simple Jaccard similarity
                score = len(intersection) / len(query_words.union(mem_words))
                scored.append((score, mem))
        
        # Sort by score
        scored.sort(key=lambda x: x[0], reverse=True)
        
        return [m[1]["text"] for m in scored[:limit]]
    
    def get_context_string(self, query: str, limit: int = 3) -> str:
        """Get formatted context string for prompt injection."""
        memories = self.retrieve(query, limit)
        if not memories:
            return ""
        
        context = "\n\n[RELEVANT MEMORIES]\n"
        for i, mem in enumerate(memories, 1):
            context += f"{i}. {mem}\n"
        return context
    
    def memorize(self, text: str) -> str:
        """Explicit memorize command."""
        mem_id = self.store(text, {"type": "explicit"})
        return f"✓ Memorized: {text[:50]}..."
    
    def list_all(self) -> List[Dict]:
        """List all memories."""
        return self.memories
    
    def forget(self, memory_id: str) -> bool:
        """Delete a memory by ID."""
        for i, mem in enumerate(self.memories):
            if mem["id"] == memory_id:
                del self.memories[i]
                self._save()
                return True
        return False
    
    def clear(self):
        """Clear all memories."""
        self.memories = []
        self._save()
