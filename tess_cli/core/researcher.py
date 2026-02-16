import json
from .logger import setup_logger
from .knowledge_base import KnowledgeBase

logger = setup_logger("Researcher")

class Researcher:
    """
    Autonomously researches unknown commands using web search and indexing.
    """
    def __init__(self, brain, knowledge_base: KnowledgeBase, web_browser):
        self.brain = brain
        self.kb = knowledge_base
        self.wb = web_browser

    def research_command(self, command_name):
        """
        Deep-dives into a command TESS doesn't know yet.
        """
        logger.info(f"🕵️ Researching unknown command: {command_name}...")
        
        # 1. Search for docs
        query = f"Windows PowerShell command {command_name} usage and examples"
        search_results = self.wb.search_google(query)
        
        if "No results" in search_results:
            return f"Research failed: No documentation found for {command_name}."

        # 2. Extract best context
        prompt = (
            f"Based on these search results, explain how to use the OS command '{command_name}'. "
            f"Provide typical syntax and 2-3 common examples.\n\n"
            f"[SEARCH RESULTS]\n{search_results}"
        )
        
        # Use Brain to summarize accurately
        summary = self.brain.think(prompt)
        
        # 3. Index it for future use
        if summary and "thinking failed" not in summary.lower():
            try:
                doc_id = f"cmd_{command_name}_researched"
                full_content = f"Command: {command_name} (Researched)\n\n[SUMMARY]\n{summary}"
                
                self.kb.collection.upsert(
                    documents=[full_content],
                    metadatas=[{"type": "command", "name": command_name, "source": "web_research"}],
                    ids=[doc_id]
                )
                logger.info(f"✅ Learned and indexed: {command_name}")
                return f"Learned about {command_name}: {summary[:200]}..."
            except Exception as e:
                logger.error(f"Failed to index researched command {command_name}: {e}")
                return f"Learned {command_name}, but indexing failed."
        
        return f"Could not research {command_name} effectively."
