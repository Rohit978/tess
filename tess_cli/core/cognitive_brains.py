import base64
import json
import os
import re
from pathlib import Path

from .config import Config
from .logger import setup_logger
from .security import SecurityEngine

logger = setup_logger("CognitiveBrains")


class ReflexBrain:
    """
    Fast deterministic router for common commands.
    This avoids invoking the LLM for obvious one-step actions.
    """

    _LAUNCH_RE = re.compile(r"^(?:open|launch|start)\s+(.+?)\s*$", re.IGNORECASE)

    def generate_command(self, user_query):
        text = (user_query or "").strip()
        lowered = text.lower()

        if not text:
            return None

        simple_system = {
            "take screenshot": {"action": "system_control", "sub_action": "screenshot"},
            "screenshot": {"action": "system_control", "sub_action": "screenshot"},
            "lock computer": {"action": "system_control", "sub_action": "lock"},
            "lock pc": {"action": "system_control", "sub_action": "lock"},
            "mute": {"action": "system_control", "sub_action": "mute"},
            "volume up": {"action": "system_control", "sub_action": "volume_up"},
            "volume down": {"action": "system_control", "sub_action": "volume_down"},
            "play pause": {"action": "system_control", "sub_action": "play_pause"},
            "pause": {"action": "system_control", "sub_action": "play_pause"},
            "list apps": {"action": "desktop_vision_op", "sub_action": "list_apps"},
            "active app": {"action": "desktop_vision_op", "sub_action": "active_app"},
            "what is open": {"action": "desktop_vision_op", "sub_action": "list_apps"},
            "what's open": {"action": "desktop_vision_op", "sub_action": "list_apps"},
            "what is on my screen": {
                "action": "desktop_vision_op",
                "sub_action": "analyze",
                "query": "Describe everything visible on the screen.",
            },
            "what's on my screen": {
                "action": "desktop_vision_op",
                "sub_action": "analyze",
                "query": "Describe everything visible on the screen.",
            },
        }
        if lowered in simple_system:
            action = dict(simple_system[lowered])
            action.setdefault("thought", "Matched a reflex command.")
            return action

        if lowered.startswith("remember that "):
            return {
                "thought": "Matched explicit memory storage.",
                "action": "memory_op",
                "sub_action": "remember",
                "content": text[len("remember that "):].strip(),
            }

        if lowered.startswith("remember "):
            return {
                "thought": "Matched explicit memory storage.",
                "action": "memory_op",
                "sub_action": "remember",
                "content": text[len("remember "):].strip(),
            }

        launch_match = self._LAUNCH_RE.match(text)
        if launch_match:
            target = launch_match.group(1).strip()
            if target and len(target.split()) <= 4:
                return {
                    "thought": "Matched an app launch reflex.",
                    "action": "launch_app",
                    "app_name": target,
                }

        return None


class TaskBrain:
    """LLM-backed action generator for non-reflex requests."""

    def __init__(self, brain):
        self.brain = brain

    def generate_command(self, user_query):
        self.brain.memory_brain.enrich_context(user_query)
        self.brain.history.append({"role": "user", "content": user_query})
        self.brain.memory_brain.distill_context()

        messages = list(self.brain.history)
        current_context = getattr(self.brain, "_current_context", "")
        if current_context:
            messages.insert(-1, {"role": "system", "content": f"[CTX]\n{current_context}\n[/CTX]"})

        response_text = self.brain._call_api_with_retry(messages, json_mode=True)
        if not response_text:
            return {"action": "error", "reason": "Brain unresponsive (Rate Limit?)"}

        cmd = self.brain._parse_json(response_text)
        self.brain.history.append({"role": "assistant", "content": json.dumps(cmd)})
        return cmd


class MemoryBrain:
    """Context retrieval and compression layer."""

    def __init__(self, brain):
        self.brain = brain

    def enrich_context(self, query):
        if len(query or "") < 4:
            return

        extras = []
        try:
            from .user_profile import UserProfile
            extras.append(UserProfile().get_facts_context())
        except Exception as e:
            logger.warning(f"Failed to load user profile context: {e}")

        if self.brain.knowledge_db:
            try:
                mem = self.brain.knowledge_db.search_memory(query, n_results=1)
                if "No match" not in mem:
                    extras.append(f"[KEY_MEMORY] {mem}")
            except Exception as e:
                logger.warning(f"Failed to search memory context: {e}")

        if Config.is_module_enabled("vault"):
            try:
                from .vault_manager import VaultManager
                vm = VaultManager()
                keys = vm.list_secrets()
                if keys:
                    extras.append(f"[VAULT] Available Keys: {', '.join(keys)}")
            except Exception as e:
                logger.warning(f"Failed to list vault keys: {e}")

        self.brain._current_context = "\n".join(filter(None, extras))

    def distill_context(self):
        if len(self.brain.history) < 80:
            return

        logger.info("Distilling history (reached 80-message budget)...")
        summary = self.brain.request_completion(
            self.brain.history + [{"role": "user", "content": "Summarize key facts concisely."}],
            temperature=0.3,
        )

        if summary:
            if self.brain.memory:
                self.brain.memory.store_memory(f"Context: {summary}")
            self.brain.history = [
                self.brain.history[0],
                {"role": "system", "content": f"[SUMMARY]\n{summary}"},
            ] + self.brain.history[-8:]
            return

        logger.warning("Distillation failed; hard-trimming to last 20 messages.")
        self.brain.history = [self.brain.history[0]] + self.brain.history[-20:]


class VisionBrain:
    """Vision-specific model calls and screen/image interpretation."""

    def __init__(self, brain):
        self.brain = brain

    def analyze_image(self, image_path, prompt):
        if not os.path.exists(image_path):
            return f"Vision Error: Screenshot file not found: {image_path}"

        client, err = self.brain._get_client()
        if not client:
            return f"Vision Error: Could not init LLM client: {err}"

        try:
            if self.brain.provider == "gemini":
                try:
                    from PIL import Image as PILImage
                    img = PILImage.open(image_path)
                except ImportError:
                    with open(image_path, "rb") as f:
                        img = {"mime_type": "image/png", "data": f.read()}
                response = client.generate_content([prompt, img])
                return response.text

            if self.brain.provider in ("openai", "groq", "deepseek", "ollama"):
                with open(image_path, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode("utf-8")
                ext = Path(image_path).suffix.lower().lstrip(".")
                mime = "image/png" if ext in ("png", "") else f"image/{ext}"
                messages = [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                        ],
                    }
                ]
                completion = client.chat.completions.create(
                    model=self.brain.model,
                    messages=messages,
                    max_tokens=1024,
                    temperature=0.3,
                )
                return completion.choices[0].message.content

            return f"Vision Error: Provider '{self.brain.provider}' does not support vision."
        except Exception as e:
            logger.error(f"Vision API Error: {e}")
            return f"Vision Error: {e}"


class PlannerBrain:
    """Placeholder facade for strategic planning ownership."""

    def __init__(self, brain):
        self.brain = brain

    def create_plan(self, goal):
        from .planner import Planner
        return Planner(self.brain).create_plan(goal)


class SocialBrain:
    """Persona and conversational policy ownership."""

    def system_prompt(self, personality):
        return Config.get_system_prompt(personality)


class SecurityBrain:
    """Action safety validation facade."""

    def __init__(self, level=None):
        self.engine = SecurityEngine(level=level or Config.get_security_level())

    def validate_action(self, action_dict):
        return self.engine.validate_action(action_dict)

    def set_level(self, level):
        return self.engine.set_level(level)
