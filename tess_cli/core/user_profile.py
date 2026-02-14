"""
TESS User Profile - Persistent Personalization
Stores user facts, preferences, and stats across sessions.
"""

import json
import os
import re
from datetime import datetime
from .logger import setup_logger

logger = setup_logger("UserProfile")

class UserProfile:
    """
    Persistent user profile that remembers facts, preferences, and usage stats.
    Stored in ~/.tess/user_profile.json
    """

    PROFILE_DIR = os.path.join(os.path.expanduser("~"), ".tess")
    PROFILE_PATH = os.path.join(PROFILE_DIR, "user_profile.json")

    DEFAULT_PROFILE = {
        "name": None,
        "nickname": None,
        "interests": [],
        "facts": [],
        "preferences": {
            "personality": "casual"  # casual, professional, witty, motivational
        },
        "stats": {
            "total_sessions": 0,
            "total_commands": 0,
            "first_session": None,
            "last_session": None,
            "current_streak": 0,
            "best_streak": 0,
            "feature_usage": {}
        }
    }

    def __init__(self):
        os.makedirs(self.PROFILE_DIR, exist_ok=True)
        self.data = self._load()
        self._update_session()

    def _load(self):
        """Load profile from disk."""
        if os.path.exists(self.PROFILE_PATH):
            try:
                with open(self.PROFILE_PATH, 'r') as f:
                    loaded = json.load(f)
                    # Merge with defaults for new fields
                    merged = self.DEFAULT_PROFILE.copy()
                    for k, v in loaded.items():
                        if isinstance(v, dict) and isinstance(merged.get(k), dict):
                            merged[k].update(v)
                        else:
                            merged[k] = v
                    return merged
            except Exception as e:
                logger.error(f"Failed to load profile: {e}")
        return self.DEFAULT_PROFILE.copy()

    def save(self):
        """Save profile to disk."""
        try:
            with open(self.PROFILE_PATH, 'w') as f:
                json.dump(self.data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save profile: {e}")

    def _update_session(self):
        """Update session stats on startup."""
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")

        self.data["stats"]["total_sessions"] += 1

        if not self.data["stats"]["first_session"]:
            self.data["stats"]["first_session"] = today

        # Streak logic
        last = self.data["stats"].get("last_session")
        if last:
            last_date = datetime.strptime(last, "%Y-%m-%d").date()
            diff = (now.date() - last_date).days
            if diff == 1:
                self.data["stats"]["current_streak"] += 1
            elif diff > 1:
                self.data["stats"]["current_streak"] = 1
            # Same day = don't change streak
        else:
            self.data["stats"]["current_streak"] = 1

        best = self.data["stats"].get("best_streak", 0)
        if self.data["stats"]["current_streak"] > best:
            self.data["stats"]["best_streak"] = self.data["stats"]["current_streak"]

        self.data["stats"]["last_session"] = today
        self.save()

    # ─── Fact Learning ────────────────────────────────────────────────────

    def learn_fact(self, fact_text, source="explicit"):
        """Store a fact about the user."""
        # Avoid duplicates
        for existing in self.data["facts"]:
            if existing["text"].lower() == fact_text.lower():
                return False

        self.data["facts"].append({
            "text": fact_text,
            "learned": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "source": source
        })
        self.save()
        logger.info(f"Learned fact: {fact_text}")
        return True

    def extract_facts_from_text(self, text):
        """
        Auto-detect and learn facts from user messages.
        Returns list of facts learned.
        """
        learned = []
        text_lower = text.lower().strip()

        # Name patterns
        name_patterns = [
            r"(?:my name is|i'm|i am|call me|they call me)\s+([A-Z][a-z]+)",
            r"(?:name's)\s+([A-Z][a-z]+)",
        ]
        for pat in name_patterns:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                name = match.group(1).strip().title()
                if len(name) > 1 and name.lower() not in ["tess", "hey", "the"]:
                    self.data["name"] = name
                    self.save()
                    learned.append(f"Name: {name}")

        # Interest / preference patterns
        interest_patterns = [
            (r"i (?:love|like|enjoy|prefer|am into)\s+(.+?)(?:\.|$|!)", "interest"),
            (r"i'm (?:a|an)\s+(.+?)(?:\.|$|!)", "identity"),
            (r"i (?:work|study|study at|work at|work as)\s+(.+?)(?:\.|$|!)", "occupation"),
            (r"my (?:favorite|fav|favourite)\s+\w+\s+is\s+(.+?)(?:\.|$|!)", "favorite"),
        ]

        for pat, fact_type in interest_patterns:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                fact = match.group(1).strip()
                if len(fact) > 2 and len(fact) < 100:
                    if self.learn_fact(fact, source=f"auto_{fact_type}"):
                        learned.append(fact)
                    # Also add to interests if it's an interest
                    if fact_type == "interest" and fact.lower() not in [i.lower() for i in self.data["interests"]]:
                        self.data["interests"].append(fact)
                        self.save()

        # "Remember that..." explicit memory
        remember_match = re.search(r"remember (?:that |this:?\s*)(.+)", text, re.IGNORECASE)
        if remember_match:
            fact = remember_match.group(1).strip()
            if len(fact) > 3:
                if self.learn_fact(fact, source="explicit"):
                    learned.append(fact)

        return learned

    def get_facts_context(self):
        """Returns a formatted string of known facts for injecting into LLM context."""
        parts = []
        if self.data["name"]:
            parts.append(f"User's name is {self.data['name']}.")
        if self.data["interests"]:
            parts.append(f"User's interests: {', '.join(self.data['interests'][:5])}.")
        for fact in self.data["facts"][-5:]:  # Last 5 facts
            parts.append(fact["text"])
        return " ".join(parts) if parts else ""

    # ─── Smart Greetings ──────────────────────────────────────────────────

    def get_greeting(self):
        """Generate a personalized, time-aware greeting."""
        now = datetime.now()
        hour = now.hour
        name = self.data.get("name") or "there"
        streak = self.data["stats"].get("current_streak", 0)
        sessions = self.data["stats"].get("total_sessions", 1)

        # Time-based greeting
        if hour < 6:
            time_greeting = f"Burning the midnight oil, {name}? 🌙"
        elif hour < 12:
            time_greeting = f"Good morning, {name}! ☀️"
        elif hour < 17:
            time_greeting = f"Good afternoon, {name}! 🌤️"
        elif hour < 21:
            time_greeting = f"Good evening, {name}! 🌆"
        else:
            time_greeting = f"Late night session, {name}! 🌙"

        # Extras
        extras = []
        if streak > 1:
            extras.append(f"🔥 {streak}-day streak!")
        if sessions == 1:
            extras.append("Welcome to your first TESS session!")
        elif sessions % 100 == 0:
            extras.append(f"🎉 Session #{sessions}! You're a power user!")
        elif sessions % 10 == 0:
            extras.append(f"Session #{sessions}")

        # Day-based flavor
        weekday = now.strftime("%A")
        if weekday == "Friday":
            extras.append("Happy Friday! 🎉")
        elif weekday == "Monday":
            extras.append("Let's crush this week! 💪")

        extra_str = "  " + " · ".join(extras) if extras else ""
        return time_greeting, extra_str

    # ─── Stats Tracking ───────────────────────────────────────────────────

    def track_command(self, action_type=None):
        """Track a command execution."""
        self.data["stats"]["total_commands"] += 1
        if action_type:
            usage = self.data["stats"].get("feature_usage", {})
            usage[action_type] = usage.get(action_type, 0) + 1
            self.data["stats"]["feature_usage"] = usage
        self.save()

    @property
    def name(self):
        return self.data.get("name")

    @property
    def personality(self):
        return self.data.get("preferences", {}).get("personality", "casual")
