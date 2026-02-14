"""
Trip Planner Skill - Plan travel itineraries.
"""

import os
from pathlib import Path
from typing import Optional


class TripPlannerSkill:
    """
    Plans trips with destinations, dates, and activities.
    """
    
    def __init__(self, brain=None, web_browser=None):
        self.brain = brain
        self.web_browser = web_browser
    
    def run(self, destination: str, dates: str, budget: Optional[str] = None,
            origin: str = "Current Location", transport_mode: str = "Any") -> str:
        """
        Plan a trip.
        
        Args:
            destination: Where to go
            dates: When (duration or dates)
            budget: Optional budget constraint
            origin: Starting location
            transport_mode: Preferred transport
            
        Returns:
            Path to saved itinerary
        """
        print(f"✈️  Planning trip to {destination}...")
        
        # Research destination
        research = ""
        if self.web_browser:
            print("  Researching destination...")
            research = self.web_browser.search(f"{destination} travel guide {dates}")
        
        # Generate itinerary
        itinerary = self._generate_itinerary(
            destination, dates, budget, origin, transport_mode, research
        )
        
        # Save
        return self._save_itinerary(destination, itinerary)
    
    def _generate_itinerary(self, destination, dates, budget, origin, transport, research) -> str:
        """Generate detailed itinerary."""
        if not self.brain:
            return f"""# Trip to {destination}

## Dates: {dates}
## Budget: {budget or 'Not specified'}

{research[:1000]}
"""
        
        prompt = f"""Create a detailed trip itinerary.

Destination: {destination}
Dates: {dates}
Budget: {budget or 'Flexible'}
From: {origin}
Transport: {transport}

Research data:
{research[:1500]}

Include:
- Day-by-day schedule
- Recommended activities
- Transport options
- Accommodation suggestions
- Budget breakdown
- Travel tips

Format as markdown."""
        
        messages = [{"role": "user", "content": prompt}]
        return self.brain.request_completion(messages, max_tokens=2000, json_mode=False) or "Planning failed"
    
    def _save_itinerary(self, destination: str, content: str) -> str:
        """Save itinerary to file."""
        from ..config_manager import get_config_manager
        config = get_config_manager()
        
        filename = f"Trip_{destination.replace(' ', '_')[:20]}.md"
        trips_dir = Path(config.config.paths.data_dir) / "trips"
        trips_dir.mkdir(parents=True, exist_ok=True)
        
        filepath = trips_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return f"Itinerary saved to: {filepath}"
