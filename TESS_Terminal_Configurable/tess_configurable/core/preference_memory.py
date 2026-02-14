"""
Preference Memory - Smart user preference tracking.
Learns and remembers user's habits, likes, dislikes, and patterns.
"""

import json
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path


class PreferenceMemory:
    """
    Intelligent preference tracking for TESS.
    
    Learns from:
    - Explicit statements ("I prefer Chrome")
    - Implicit patterns (user always opens Chrome)
    - Corrections (user corrects TESS choice)
    
    Categories:
    - Software preferences (browser, editor, etc.)
    - Time patterns (morning routine, work hours)
    - Communication style (formal, casual)
    - Task patterns (common workflows)
    """
    
    def __init__(self, user_id: str = "default", memory_dir: Optional[str] = None):
        self.user_id = user_id
        
        if memory_dir is None:
            from ..config_manager import get_config_manager
            config = get_config_manager()
            memory_dir = config.config.paths.memory_dir
        
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        
        self.prefs_file = self.memory_dir / f"{user_id}_preferences.json"
        
        # Preference categories
        self.preferences: Dict[str, Any] = {
            "software": {},      # browser, editor, terminal, etc.
            "patterns": {},      # time patterns, routines
            "communication": {}, # style preferences
            "context": {},       # current task, project
            "facts": {},         # facts about user
        }
        
        self._load()
    
    def _load(self):
        """Load preferences from file."""
        if self.prefs_file.exists():
            try:
                with open(self.prefs_file, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    self.preferences.update(loaded)
            except Exception as e:
                print(f"Error loading preferences: {e}")
    
    def _save(self):
        """Save preferences to file."""
        try:
            with open(self.prefs_file, 'w', encoding='utf-8') as f:
                json.dump(self.preferences, f, indent=2)
        except Exception as e:
            print(f"Error saving preferences: {e}")
    
    def learn_from_statement(self, statement: str) -> Optional[str]:
        """
        Extract preference from user statement.
        
        Args:
            statement: User's statement (e.g., "I prefer Chrome over Firefox")
            
        Returns:
            What was learned, or None
        """
        statement_lower = statement.lower()
        learned = []
        
        # Pattern: "I prefer X" / "I like X" / "I use X"
        prefer_patterns = [
            r"i (?:prefer|like|use|love) (\w+)",
            r"my favorite (\w+) is (\w+)",
            r"i always use (\w+)",
            r"(\w+) is better than",
        ]
        
        for pattern in prefer_patterns:
            match = re.search(pattern, statement_lower)
            if match:
                preference = match.group(1)
                
                # Categorize
                category = self._categorize_preference(preference)
                
                # Store
                self.set_preference(category, preference, "explicit", confidence=0.9)
                learned.append(f"{category}: {preference}")
        
        # Pattern: "I don't like X" / "I hate X"
        dislike_patterns = [
            r"i (?:don't like|dislike|hate) (\w+)",
        ]
        
        for pattern in dislike_patterns:
            match = re.search(pattern, statement_lower)
            if match:
                disliked = match.group(1)
                self.set_preference("dislikes", disliked, "explicit", confidence=0.9)
                learned.append(f"dislike: {disliked}")
        
        # Pattern: "I work from X to Y"
        time_pattern = r"i work from (\d+)(?::\d+)?\s*(am|pm)? to (\d+)(?::\d+)?\s*(am|pm)?"
        match = re.search(time_pattern, statement_lower)
        if match:
            start_hour = match.group(1)
            start_period = match.group(2) or ""
            end_hour = match.group(3)
            end_period = match.group(4) or ""
            
            self.set_preference("patterns", "work_hours", {
                "start": f"{start_hour}{start_period}",
                "end": f"{end_hour}{end_period}"
            }, confidence=0.95)
            learned.append("work_hours pattern")
        
        # Pattern: "My name is X" / "I am X"
        name_pattern = r"(?:my name is|i am|call me) (\w+)"
        match = re.search(name_pattern, statement_lower)
        if match:
            name = match.group(1)
            self.set_fact("name", name)
            learned.append(f"name: {name}")
        
        # Save if learned something
        if learned:
            self._save()
            return f"Learned: {', '.join(learned)}"
        
        return None
    
    def learn_from_action(self, action_type: str, choice: str, context: Dict = None):
        """
        Learn preference from user's action (implicit learning).
        
        Args:
            action_type: Type of action (e.g., "browser", "editor")
            choice: What user chose
            context: Additional context
        """
        # Track frequency
        current = self.get_preference("software", action_type, {})
        
        if isinstance(current, dict):
            current[choice] = current.get(choice, 0) + 1
        else:
            current = {choice: 1}
        
        self.set_preference("software", action_type, current)
        
        # If consistently chosen, make it the preferred option
        total = sum(current.values())
        if total >= 3:  # After 3 uses
            most_common = max(current, key=current.get)
            if current[most_common] / total > 0.7:  # 70% of the time
                self.set_preference("software", f"preferred_{action_type}", most_common, 
                                   confidence=min(0.5 + (total * 0.1), 0.95))
        
        self._save()
    
    def learn_from_correction(self, attempted: str, corrected: str, context: str):
        """
        Learn when user corrects TESS.
        
        Args:
            attempted: What TESS tried
            corrected: What user wanted instead
            context: Context of the correction
        """
        # Store correction
        corrections = self.get_preference("learning", "corrections", [])
        corrections.append({
            "attempted": attempted,
            "corrected": corrected,
            "context": context,
            "timestamp": datetime.now().isoformat()
        })
        
        # Keep only last 20 corrections
        corrections = corrections[-20:]
        self.set_preference("learning", "corrections", corrections)
        
        # Update preference based on correction
        self.set_preference("software", context, corrected, confidence=0.95)
        
        self._save()
    
    def get_preference(self, category: str, key: str, default=None):
        """Get a specific preference."""
        return self.preferences.get(category, {}).get(key, default)
    
    def set_preference(self, category: str, key: str, value: Any, 
                      source: str = "inferred", confidence: float = 0.5):
        """
        Set a preference.
        
        Args:
            category: Preference category
            key: Preference key
            value: Preference value
            source: How it was learned (explicit, inferred, correction)
            confidence: Confidence level (0-1)
        """
        if category not in self.preferences:
            self.preferences[category] = {}
        
        # Store with metadata
        self.preferences[category][key] = {
            "value": value,
            "source": source,
            "confidence": confidence,
            "updated_at": datetime.now().isoformat()
        }
    
    def get_software_preference(self, software_type: str) -> Optional[str]:
        """Get preferred software choice."""
        # Check for explicit preference first
        explicit = self.get_preference("software", f"preferred_{software_type}")
        if explicit and isinstance(explicit, dict):
            return explicit.get("value")
        elif explicit:
            return explicit
        
        # Check frequency-based preference
        freq = self.get_preference("software", software_type, {})
        if isinstance(freq, dict) and freq:
            return max(freq, key=freq.get)
        
        return None
    
    def set_fact(self, key: str, value: Any):
        """Store a fact about the user."""
        self.set_preference("facts", key, value, source="explicit", confidence=0.95)
    
    def get_fact(self, key: str) -> Optional[Any]:
        """Get a fact about the user."""
        fact = self.get_preference("facts", key)
        if isinstance(fact, dict):
            return fact.get("value")
        return fact
    
    def _categorize_preference(self, preference: str) -> str:
        """Categorize a preference."""
        browsers = ["chrome", "firefox", "edge", "safari", "brave", "opera"]
        editors = ["vscode", "code", "sublime", "atom", "notepad++", "vim", "emacs"]
        terminals = ["powershell", "cmd", "bash", "zsh", "terminal", "iterm"]
        
        pref_lower = preference.lower()
        
        if pref_lower in browsers:
            return "browser"
        elif pref_lower in editors:
            return "editor"
        elif pref_lower in terminals:
            return "terminal"
        else:
            return "general"
    
    def get_context_prompt(self) -> str:
        """Generate context prompt for LLM based on preferences."""
        context_parts = []
        
        # Software preferences
        browser = self.get_software_preference("browser")
        if browser:
            context_parts.append(f"User prefers {browser} browser")
        
        editor = self.get_software_preference("editor")
        if editor:
            context_parts.append(f"User prefers {editor} editor")
        
        # Facts
        name = self.get_fact("name")
        if name:
            context_parts.append(f"User's name is {name}")
        
        # Work patterns
        work_hours = self.get_preference("patterns", "work_hours")
        if work_hours and isinstance(work_hours, dict):
            value = work_hours.get("value", work_hours)
            context_parts.append(f"User works {value['start']} to {value['end']}")
        
        if context_parts:
            return "\n".join(["[USER CONTEXT]"] + context_parts + ["[/USER CONTEXT]"])
        
        return ""
    
    def summarize_preferences(self) -> str:
        """Get a summary of all preferences."""
        lines = ["User Preferences Summary:", "-" * 40]
        
        for category, prefs in self.preferences.items():
            if prefs:
                lines.append(f"\n{category.upper()}:")
                for key, value in prefs.items():
                    if isinstance(value, dict):
                        val = value.get("value", value)
                        conf = value.get("confidence", "?")
                        lines.append(f"  • {key}: {val} (confidence: {conf})")
                    else:
                        lines.append(f"  • {key}: {value}")
        
        return "\n".join(lines)
    
    def export(self) -> Dict:
        """Export all preferences."""
        return self.preferences.copy()
    
    def clear_category(self, category: str):
        """Clear all preferences in a category."""
        if category in self.preferences:
            self.preferences[category] = {}
            self._save()
    
    def clear_all(self):
        """Clear all preferences."""
        self.preferences = {
            "software": {},
            "patterns": {},
            "communication": {},
            "context": {},
            "facts": {},
        }
        self._save()
