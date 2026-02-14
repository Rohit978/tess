"""
Knowledge Base - Vector database for semantic search.
Uses ChromaDB for embeddings and search.
"""

import os
from pathlib import Path
from typing import Optional, List


class KnowledgeBase:
    """
    Manages long-term knowledge using ChromaDB.
    """
    
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            from ..config_manager import get_config_manager
            config = get_config_manager()
            db_path = config.config.paths.vector_db
        
        self.db_path = Path(db_path)
        self.db_path.mkdir(parents=True, exist_ok=True)
        
        self.client = None
        self.collection = None
        self._init_chroma()
    
    def _init_chroma(self):
        """Initialize ChromaDB."""
        try:
            import chromadb
            from chromadb.utils import embedding_functions
            
            self.client = chromadb.PersistentClient(path=str(self.db_path))
            
            # Use default embedding function
            self.embedding_fn = embedding_functions.DefaultEmbeddingFunction()
            
            self.collection = self.client.get_or_create_collection(
                name="tess_knowledge",
                embedding_function=self.embedding_fn
            )
            
        except ImportError:
            print("ChromaDB not installed. Run: pip install chromadb")
        except Exception as e:
            print(f"ChromaDB init error: {e}")
    
    def learn_directory(self, path: str) -> str:
        """
        Index all files in a directory.
        
        Args:
            path: Directory to index
            
        Returns:
            Status message
        """
        if not self.collection:
            return "Knowledge base not initialized"
        
        source = Path(path)
        if not source.exists():
            return f"Path not found: {path}"
        
        text_extensions = {'.py', '.md', '.txt', '.json', '.js', '.html', '.css', '.java', '.cpp'}
        count = 0
        
        for file_path in source.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in text_extensions:
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    if not content.strip():
                        continue
                    
                    # Chunk content
                    chunks = [content[i:i+1000] for i in range(0, len(content), 1000)]
                    
                    ids = [f"{file_path}_{i}" for i in range(len(chunks))]
                    metadatas = [{"source": str(file_path), "chunk": i} for i in range(len(chunks))]
                    
                    self.collection.upsert(
                        documents=chunks,
                        ids=ids,
                        metadatas=metadatas
                    )
                    count += 1
                    
                except Exception as e:
                    print(f"Error indexing {file_path}: {e}")
        
        return f"Indexed {count} files from {path}"
    
    def search(self, query: str, n_results: int = 3) -> str:
        """
        Search knowledge base.
        
        Args:
            query: Search query
            n_results: Number of results
            
        Returns:
            Formatted search results
        """
        if not self.collection:
            return "Knowledge base not initialized"
        
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results
            )
            
            if not results['documents'] or not results['documents'][0]:
                return "No matching knowledge found"
            
            output = []
            for i, doc in enumerate(results['documents'][0]):
                source = results['metadatas'][0][i].get('source', 'unknown')
                output.append(f"[Source: {source}]\n{doc[:500]}...")
            
            return "\n\n".join(output)
            
        except Exception as e:
            return f"Search error: {e}"
    
    def store_memory(self, text: str, metadata: Optional[dict] = None) -> bool:
        """Store a memory/document."""
        if not self.collection:
            return False
        
        try:
            import time
            doc_id = f"mem_{int(time.time()*1000)}"
            
            self.collection.add(
                documents=[text],
                metadatas=[metadata or {"type": "memory"}],
                ids=[doc_id]
            )
            return True
        except Exception as e:
            print(f"Store error: {e}")
            return False
    
    def get_stats(self) -> str:
        """Get knowledge base statistics."""
        if not self.collection:
            return "Knowledge base not initialized"
        
        try:
            count = self.collection.count()
            return f"Knowledge Base: {count} documents indexed"
        except Exception as e:
            return f"Stats error: {e}"
