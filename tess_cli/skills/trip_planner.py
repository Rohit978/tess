import os
import json
import time
from ..core.logger import setup_logger
from ..core.config import Config

logger = setup_logger("TripPlanner")

class TripPlannerSkill:
    """
    Skill for autonomous trip planning (Interactive & Real Search).
    """
    def __init__(self, brain, web_browser=None):
        self.brain = brain
        self.web_browser = web_browser

    def run(self, destination, dates, budget=None, origin="Current Location", transport_mode="Any"):
        """
        Executes the trip planning workflow with visible research.
        """
        logger.info(f"Starting trip plan: {destination}, {dates} (Mode: {transport_mode})")
        
        # 1. Research Destination
        logger.info("Researching destination (Visible)...")
        research_query = f"best things to do in {destination} in {dates} travel guide"
        research_results = self._web_search(research_query)
        
        # 2. Logistics (Transport) - Tailored to Mode
        logger.info(f"Researching transport ({transport_mode})...")
        if transport_mode and transport_mode.lower() != "any":
             transport_query = f"{transport_mode} prices from {origin} to {destination} {dates}"
        else:
             transport_query = f"how to get to {destination} from {origin} {dates} options"
             
        if budget:
            transport_query += f" budget {budget}"
            
        transport_results = self._web_search(transport_query)
        
        # 3. Deep Dive (Hotels/Stays) - Tailored to Budget
        logger.info("Researching Hotels...")
        hotel_query = f"best hotels in {destination} for {dates}"
        if budget:
            hotel_query += f" price under {budget}"
            
        hotel_results = self._web_search(hotel_query)
        
        # 4. Synthesize Plan via LLM
        logger.info("Synthesizing plan...")
        final_plan = self._synthesize_plan(
            destination, dates, budget, origin, transport_mode,
            research_results, transport_results, hotel_results
        )
        
        # 5. Save to File
        filename = f"Trip_To_{destination.replace(' ', '_')}.md"
        desktop = Config.get_desktop_path()
        filepath = os.path.join(desktop, filename)
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(final_plan)
            
        return f"Trip plan saved to {filepath}"

    def _web_search(self, query):
        """Uses WebBrowser for REAL VISIBLE search."""
        if not self.web_browser:
            return "[WebBrowser not available for search]"
            
        try:
            # Headless=False for user visibility as requested
            return self.web_browser.search_sync(query, headless=False)
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return f"[Search Error: {e}]"

    def _synthesize_plan(self, dest, dates, budget, origin, mode, research, transport, hotels):
        prompt = f"""
        You are an expert TRAVEL AGENT specializing in INDIAN TRAVEL. Create a detailed trip itinerary.
        
        DETAILS:
        - Destination: {dest}
        - Dates: {dates}
        - Origin: {origin}
        - Budget: {budget or 'Flexible'}
        - Preferred Mode: {mode or 'Any'}
        
        CONTEXT (Research):
        {research}
        
        LOGISTICS (Transport):
        {transport}
        
        HOTELS/STAYS:
        {hotels}
        
        OUTPUT FORMAT:
        Markdown.
        
        IMPORTANT:
        - All prices MUST be in Indian Rupees (₹).
        - Focus on local Indian cultural nuances and practical travel tips for India.
        
        STRUCTURE:
        # Trip to {dest}
        ## Logistics
        - **Transport**: Options ({mode})...
        - **Hotels**: Recommendations based on budget...
        
        ## Itinerary
        - **Day 1**: ...
        - **Day 2**: ...
        
        ## Budget Estimates (in ₹)
        ...
        """
        
        # Use Brain to generate text
        messages = [{"role": "system", "content": prompt}]
        return self.brain.request_completion(messages, json_mode=False)
