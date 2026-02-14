import os
import chromadb
from chromadb.utils import embedding_functions
from .logger import setup_logger

logger = setup_logger("KnowledgeBase")

class KnowledgeBase:
    """
    Manages long-term memory using ChromaDB.
    """
    
    def __init__(self, db_path="vector_db"):
        self.client = chromadb.PersistentClient(path=db_path)
        
        # Use simple default embedding function (all-MiniLM-L6-v2) logic handled by chroma or explicit
        # For simplicity, we stick to default for now which downloads a small model
        self.embedding_fn = embedding_functions.DefaultEmbeddingFunction()
        
        self.collection = self.client.get_or_create_collection(
            name="tess_knowledge",
            embedding_function=self.embedding_fn
        )
        
    def _chunk_text(self, text, max_chars=1000, overlap=100):
        """
        Splits text into chunks of max_chars with overlap.
        """
        chunks = []
        start = 0
        text_len = len(text)
        
        while start < text_len:
            end = start + max_chars
            chunk = text[start:end]
            chunks.append(chunk)
            
            # Move start forward, but backtrack by overlap
            start += max_chars - overlap
            
        return chunks

    def learn_directory(self, path="."):
        """
        Recursively reads and indexes text files in the directory.
        """
        path = os.path.abspath(path)
        if not os.path.exists(path):
            return f"Error: Path {path} not found."
            
        logger.info(f"Indexing directory: {path}")
        count = 0
        
        text_extensions = {'.py', '.md', '.txt', '.json', '.js', '.html', '.css', '.c', '.cpp', '.h', '.java'}
        
        for root, _, files in os.walk(path):
            if "vector_db" in root or ".git" in root or "__pycache__" in root:
                continue
                
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in text_extensions:
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            
                        if not content.strip():
                            continue
                            
                        # Chunking strategy: Properly recursive
                        chunks = self._chunk_text(content, max_chars=1500, overlap=150)
                        
                        ids = [f"{file_path}_{i}" for i in range(len(chunks))]
                        metadatas = [{"source": file_path, "chunk_index": i, "total_chunks": len(chunks)} for i in range(len(chunks))]
                        
                        self.collection.upsert(
                            documents=chunks,
                            ids=ids,
                            metadatas=metadatas
                        )
                        count += 1
                        print(f"Indexed: {file_path}")
                        
                    except Exception as e:
                        logger.error(f"Failed to index {file_path}: {e}")
                        
        return f"Successfully indexed {count} files in '{path}'."

    def search(self, query, n_results=3):
        """
        Semantic search for the query.
        """
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results
            )
            
            # Formatting results
            output = ""
            if not results['documents']:
                return "No matching knowledge found."
                
            for i, doc in enumerate(results['documents'][0]):
                meta = results['metadatas'][0][i]
                source = meta.get('source', 'unknown')
                output += f"\n--- [Source: {source}] ---\n{doc}\n"
                
            return output
        except Exception as e:
            logger.error(f"Search error: {e}")
            return f"Error searching knowledge base: {e}"

    def get_stats(self):
        """
        Returns statistics about the knowledge base (count, sources).
        """
        try:
            count = self.collection.count()
            # Getting unique sources is expensive in simple Chroma Setup without metadata filtering tricks
            # or separate tracking. For now, we just return the count and maybe a sample.
            # We can peek at the first 10 items to show examples.
            
            peek = self.collection.peek(limit=5)
            sources = set()
            if peek and 'metadatas' in peek:
                for meta in peek['metadatas']:
                    if 'source' in meta:
                        sources.add(os.path.basename(meta['source']))
            
            source_list = ", ".join(list(sources))
            return f"Knowledge Base Stats:\n- Total Chunks: {count}\n- Sample Sources: {source_list}..."
        except Exception as e:
            return f"Error getting stats: {e}"

    def store_memory(self, text, metadata=None):
        """
        Stores a conversation snippet or fact into the vector DB.
        """
        try:
            if not metadata:
                metadata = {"type": "conversation", "timestamp": "unknown"}
                
            import time
            doc_id = f"mem_{int(time.time()*1000)}"
            
            self.collection.add(
                documents=[text],
                metadatas=[metadata],
                ids=[doc_id]
            )
            return True
        except Exception as e:
            logger.error(f"Failed to store memory: {e}")
            return False

    def search_memory(self, query, n_results=3):
        """
        Searches strictly for conversation/memory items.
        """
        return self.search(query, n_results)
