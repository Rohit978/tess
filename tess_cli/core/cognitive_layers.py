import os
import json
import re
import logging
from typing import Dict, List, Any, Optional
from .config import Config
from .event_bus import event_bus

logger = logging.getLogger("CognitiveLayers")

class MemoryCentricCore:
    """
    Persistent repository for Structured, Procedural, and Episodic memories.
    Acts as the massive memory system working in tandem with the tiny reasoning core.
    """
    def __init__(self, user_id: str = "default"):
        self.user_id = user_id
        self.tess_dir = os.path.join(os.path.expanduser("~"), ".tess")
        os.makedirs(self.tess_dir, exist_ok=True)
        
        self.memory_file = os.path.join(self.tess_dir, f"memory_centric_{user_id}.json")
        self.data = {
            "structured_memory": {},   # Key-value facts and variables
            "procedural_memory": [],   # Executable workflow graphs
            "episodic_memory": []      # Short log of recent successful query -> action chains
        }
        self.load()

    def load(self):
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, "r") as f:
                    loaded = json.load(f)
                    # Safe deep merge: only overwrite keys that exist and match type
                    for key in self.data:
                        if key in loaded and isinstance(loaded[key], type(self.data[key])):
                            self.data[key] = loaded[key]
            except Exception as e:
                logger.error(f"Failed to load memory centric database: {e}")

    def save(self):
        try:
            with open(self.memory_file, "w") as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save memory centric database: {e}")

    def store_fact(self, key: str, value: Any):
        self.data["structured_memory"][key] = value
        self.save()

    def get_fact(self, key: str, default: Any = None) -> Any:
        return self.data["structured_memory"].get(key, default)


class ProceduralLearner:
    """
    Phase 6: Automatic procedural learning and instinct compilation.
    Tracks command sequences and compiles repeated workflows into executable graphs.
    """
    def __init__(self, memory_core: MemoryCentricCore):
        self.memory_core = memory_core
        # Track active session execution history
        self.current_session_history: List[Dict[str, Any]] = []
        self.last_query = ""

        # Subscribe to command execution events to record habits
        event_bus.subscribe("command_executed", self._on_command_executed)

    def record_query(self, query: str):
        self.last_query = query.strip()
        self.current_session_history = []

    def _on_command_executed(self, action_data: Dict[str, Any]):
        """Callback from the event bus when any command finishes execution."""
        if not self.last_query:
            return
        
        # Don't record reflex commands, error actions, or replies as part of procedural steps
        action = action_data.get("action")
        if action in ("reply_op", "final_reply", "error") or "matched a reflex" in str(action_data.get("thought", "")).lower():
            return
            
        self.current_session_history.append(action_data)
        
        # Once we receive final reply or the agent task finishes, we can commit the episode
        # (This is simulated by storing episodic logs)

    def commit_episode(self, success: bool = True):
        """Commits the current query -> action chain to episodic memory."""
        if not self.last_query or not self.current_session_history or not success:
            self.last_query = ""
            return
            
        # Clean up actions (only keep action and its essential parameters)
        cleaned_steps = []
        for step in self.current_session_history:
            step_copy = dict(step)
            # Remove keys like 'thought' to keep memory lightweight
            step_copy.pop("thought", None)
            cleaned_steps.append(step_copy)

        episodic_entry = {
            "query": self.last_query.lower(),
            "steps": cleaned_steps
        }

        # Add to episodic memory
        self.memory_core.data["episodic_memory"].append(episodic_entry)
        # Keep episodic memory capped at 50 entries
        if len(self.memory_core.data["episodic_memory"]) > 50:
            self.memory_core.data["episodic_memory"].pop(0)

        self._check_and_compile_habits()
        self.memory_core.save()
        
        # Reset tracker
        self.last_query = ""
        self.current_session_history = []

    def _check_and_compile_habits(self):
        """
        Phase 6: Compresses repeated workflows into executable procedural graphs.
        If a user repeats a query or query-pattern multiple times, it learns a Habit.
        """
        # Count frequency of queries in episodic memory
        query_counts = {}
        for entry in self.memory_core.data["episodic_memory"]:
            q = entry["query"]
            query_counts[q] = query_counts.get(q, 0) + 1

        for query, count in query_counts.items():
            # If a workflow is repeated 3 or more times, compile it into an executable graph!
            if count >= 3:
                # Check if we already compiled this habit
                exists = any(query in graph["trigger_phrases"] for graph in self.memory_core.data["procedural_memory"])
                if not exists:
                    # Find all steps associated with this query to construct the graph
                    matching_episodes = [e for e in self.memory_core.data["episodic_memory"] if e["query"] == query]
                    if matching_episodes:
                        # Compile graph using the latest execution steps
                        steps = matching_episodes[-1]["steps"]
                        new_graph = {
                            "name": f"habit_{query.replace(' ', '_')}",
                            "trigger_phrases": [query],
                            "steps": steps
                        }
                        self.memory_core.data["procedural_memory"].append(new_graph)
                        logger.info(f"💡 Procedural instinct compiled: learned habit for query '{query}'")
                        event_bus.publish("procedural_graph_learned", new_graph)

    def find_learned_workflow(self, query: str) -> Optional[Dict[str, Any]]:
        """Checks if the query matches any compiled procedural graph."""
        lowered = query.strip().lower()
        for graph in self.memory_core.data["procedural_memory"]:
            if lowered in graph["trigger_phrases"]:
                return graph
            # Check for close substring / regex matches to allow natural variation
            for phrase in graph["trigger_phrases"]:
                # Require at least 60% length overlap to prevent partial matches
                shorter = min(len(phrase), len(lowered))
                longer = max(len(phrase), len(lowered))
                if (phrase in lowered or lowered in phrase) and shorter / longer > 0.6:
                    return graph
        return None


class CognitiveRouter:
    """
    Phase 3 & 4: Replaces static prompting with policy graphs,
    temporary cognition contexts, and layered cognitive routing.
    """
    def __init__(self, brain):
        self.brain = brain
        self.memory_core = MemoryCentricCore(user_id=brain.user_id)
        self.procedural_learner = ProceduralLearner(self.memory_core)
        self.last_reflex_result = None

    def route(self, query: str) -> str:
        """
        Learned Routing / Classification.
        Decides the cognitive layer needed: 'reflex', 'habit', 'planner', or 'reasoner'.
        """
        lowered = query.strip().lower()

        # 1. Reflex Check (deterministic instant patterns)
        reflex_result = self.brain.reflex_brain.generate_command(query)
        self.last_reflex_result = reflex_result
        if reflex_result is not None:
            return "reflex"

        # 2. Habit Check (procedural skill memory)
        if self.procedural_learner.find_learned_workflow(query) is not None:
            return "habit"

        # 3. Planner Check (multi-step requests)
        planning_triggers = [
            "plan", "scaffold", "build", "release", "workflow", "automate", 
            "setup", "create a project",
            "make a script to", "sequence", "schedule"
        ]
        if any(trigger in lowered for trigger in planning_triggers) or len(lowered.split()) > 20:
            return "planner"

        # 4. Fallback to Deep Reasoner (conversational or complex novel queries)
        return "reasoner"

    def get_temporary_cognition_context(self, active_layer: str, original_prompt: str) -> str:
        """
        Phase 3: Dynamic context assembly instead of monolithic system prompts.
        Builds a minimal context tailored to the active layer, saving token footprint.
        """
        base_context = (
            "SYSTEM ACTIVE: TESS Split-Brain Protocol.\n"
            f"Active Cognition Layer: {active_layer.upper()}\n"
            f"User Personality Override: {self.brain.personality.upper()}\n"
        )
        
        # Load structured memory context
        facts = self.memory_core.data["structured_memory"]
        facts_str = ", ".join([f"{k}={v}" for k, v in facts.items()])
        if facts_str:
            base_context += f"Structured Memory Context: [{facts_str}]\n"

        if active_layer == "reflex":
            return base_context + "Goal: Instant deterministic action mapping. No LLM compute required."
        elif active_layer == "habit":
            return base_context + "Goal: Executing cached procedural graph steps directly."
        elif active_layer == "planner":
            return original_prompt + "\n\n" + base_context + (
                "Goal: Structured decomposition. Outline steps logically, coordinate actions carefully, "
                "verify results step-by-step, and output 'final_reply' when complete."
            )
        else: # reasoner
            return original_prompt + "\n\n" + base_context + (
                "Goal: Resolve novel complex issue or engaging user interaction. "
                "Apply empathetic persona formatting, respect system rules, and formulate precise JSON responses."
            )

