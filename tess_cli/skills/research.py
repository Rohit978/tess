import os
import time
from ..core.logger import setup_logger
from ..core.config import Config

logger = setup_logger("ResearchSkill")

class ResearchSkill:
    """
    Skill for Deep Research.
    Performs multi-step research: Plan -> Search -> Scrape -> Synthesize.
    """
    def __init__(self, brain, google_client, web_browser):
        self.brain = brain
        self.google_client = google_client
        self.web_browser = web_browser

    def run(self, topic, depth=3):
        """
        Executes the research workflow.
        """
        logger.info(f"Starting deep research on: {topic} (Depth: {depth})")
        
        # 1. Plan Research Plan
        plan_prompt = f"Break down this research topic into {depth} specific search queries to cover it comprehensively: '{topic}'. Return ONLY a JSON list of strings."
        plan_json = self.brain.think(plan_prompt)
        
        # Clean JSON if needed
        import json
        import re
        queries = []
        try:
            # Try to extract JSON list
            match = re.search(r"\[.*\]", plan_json, re.DOTALL)
            if match:
                queries = json.loads(match.group(0))
            else:
                queries = [topic] # Fallback
        except:
            queries = [topic]
            
        logger.info(f"Research Plan: {queries}")
        
        # 2. Search & Scrape
        knowledge_base = ""
        
        for q in queries:
            logger.info(f"Researching sub-topic: {q}")
            
            # Search Google
            if not self.google_client:
                logger.warning("GoogleClient not available. Skipping search.")
                continue
                
            # We need a search method in GoogleClient for generic queries, 
            # currently it has list_emails/events. 
            # WAIT: GoogleClient uses Gmail/Calendar API. It does NOT do Google Search.
            # We should use WebBrowser.search_sync() for Google Search!
            
            # Actually, `web_browser.search_sync(q)` returns a string summary/snippets.
            # That is perfect for research.
            
            if not self.web_browser:
                logger.warning("WebBrowser not available.")
                break
                
            results_text = self.web_browser.search_sync(q)
            knowledge_base += f"\n\n### Findings for '{q}':\n{results_text}"
            
            # Optional: If we want DEEP scraping, we'd parse URLs from results and visit them.
            # For v1, `search_sync` snippets + featured answers are usually enough and faster.
            # Let's stick to search_sync results for now to be polite to target sites.
            
        if not knowledge_base:
            return "Research failed. No information found or tools missing."
            
        # 3. Synthesize Report
        logger.info("Synthesizing Report...")
        report = self._synthesize_report(topic, knowledge_base)
        
        # 4. Save Report
        filename = f"Research_{topic.replace(' ', '_')[:20]}.md"
        desktop = Config.get_desktop_path()
        filepath = os.path.join(desktop, "TESS_Research", filename)
        
        # Ensure dir exists
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(report)
            
        return f"Research complete. Report saved to {filepath}"

    def _synthesize_report(self, topic, knowledge):
        prompt = f"""
        You are an expert Researcher. Write a comprehensive report on: "{topic}".
        
        BASE YOUR REPORT ON THE FOLLOWING RESEARCH DATA:
        {knowledge}
        
        FORMAT:
        # {topic}
        [Executive Summary]
        
        ## Key Findings
        ...
        
        ## Detailed Analysis
        ...
        
        ## Sources / References
        (Cite the domains/links found in the data)
        
        STYLE:
        Professional, objective, detailed. Use Markdown.
        """
        
        # Increase max tokens for report
        messages = [{"role": "system", "content": prompt}]
        return self.brain.request_completion(messages, max_tokens=2000, json_mode=False)
