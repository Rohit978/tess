"""
Research Skill - Deep research on topics.
"""

import os
from pathlib import Path
from typing import Optional


class ResearchSkill:
    """
    Performs multi-step research: Plan → Search → Synthesize.
    """
    
    def __init__(self, brain=None, web_browser=None):
        self.brain = brain
        self.web_browser = web_browser
    
    def run(self, topic: str, depth: int = 3) -> str:
        """
        Execute research workflow.
        
        Args:
            topic: Research topic
            depth: Number of sub-queries
            
        Returns:
            Path to saved report
        """
        print(f"🔬 Starting deep research on: {topic}")
        
        # 1. Generate research plan
        queries = self._generate_queries(topic, depth)
        print(f"Research plan: {queries}")
        
        # 2. Gather information
        knowledge = ""
        for query in queries:
            print(f"  Searching: {query}")
            if self.web_browser:
                results = self.web_browser.search(query)
                knowledge += f"\n\n### {query}\n{results}"
        
        # 3. Synthesize report
        print("Synthesizing report...")
        report = self._synthesize(topic, knowledge)
        
        # 4. Save report
        return self._save_report(topic, report)
    
    def _generate_queries(self, topic: str, depth: int) -> list:
        """Generate search queries from topic."""
        if not self.brain:
            # Fallback
            return [topic, f"{topic} overview", f"{topic} latest"][:depth]
        
        prompt = f"""Break down this research topic into {depth} specific search queries.
Topic: {topic}

Return ONLY a JSON list like: ["query 1", "query 2", ...]"""
        
        try:
            response = self.brain.think(prompt)
            import json
            import re
            
            match = re.search(r'\[.*\]', response, re.DOTALL)
            if match:
                return json.loads(match.group(0))
        except:
            pass
        
        return [topic]
    
    def _synthesize(self, topic: str, knowledge: str) -> str:
        """Synthesize final report."""
        if not self.brain:
            return f"# Research: {topic}\n\n{knowledge[:2000]}"
        
        prompt = f"""Write a comprehensive research report on: "{topic}"

Based on this research data:
{knowledge[:3000]}

Format:
# {topic}

## Executive Summary
Brief overview

## Key Findings
Main points

## Detailed Analysis
In-depth coverage

## Sources
Mentioned sources

Style: Professional, objective, well-structured."""
        
        messages = [{"role": "user", "content": prompt}]
        return self.brain.request_completion(messages, max_tokens=2000, json_mode=False) or "Synthesis failed"
    
    def _save_report(self, topic: str, report: str) -> str:
        """Save report to file."""
        from ..config_manager import get_config_manager
        config = get_config_manager()
        
        filename = f"Research_{topic.replace(' ', '_')[:30]}.md"
        reports_dir = Path(config.config.paths.data_dir) / "research"
        reports_dir.mkdir(parents=True, exist_ok=True)
        
        filepath = reports_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report)
        
        return f"Report saved to: {filepath}"
