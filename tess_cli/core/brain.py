import json
import re
import os
import time
import warnings
import logging
import random

# Suppress warnings
warnings.filterwarnings("ignore", category=FutureWarning)
import google.generativeai as genai
from groq import Groq
from openai import OpenAI

from .config import Config
from .logger import setup_logger
from .memory_engine import MemoryEngine

logger = setup_logger("Brain")

class LLMClientFactory:
    """Factory to create LLM clients."""
    @staticmethod
    def get_client(provider, model, api_key):
        if not api_key: return None, f"Missing API Key for {provider}"
        try:
            if provider == "groq": return Groq(api_key=api_key), None
            elif provider == "openai": return OpenAI(api_key=api_key), None
            elif provider == "deepseek": return OpenAI(api_key=api_key, base_url="https://api.deepseek.com"), None
            elif provider == "gemini":
                genai.configure(api_key=api_key)
                return genai.GenerativeModel(model), None
        except Exception as e:
            return None, str(e)
        return None, "Unknown Provider"

class Brain:
    """
    Handles LLM interactions with robust retries and failover.
    """
    def __init__(self, user_id="default", knowledge_db=None, personality="casual"):
        self.user_id = str(user_id)
        self.personality = personality
        self.history = [{"role": "system", "content": Config.get_system_prompt(personality)}]
        
        self.memory = MemoryEngine(user_id=self.user_id)
        self.knowledge_db = knowledge_db 
        self.provider = Config.LLM_PROVIDER
        self.model = Config.LLM_MODEL
        self.current_key_index = 0
        
        logger.info(f"Brain Initialized | Provider: {self.provider.upper()} | Model: {self.model}")

    def update_history(self, role, content):
        self.history.append({"role": role, "content": content})

    def _get_client(self):
        key = Config.get_api_key(self.provider, index=self.current_key_index)
        return LLMClientFactory.get_client(self.provider, self.model, key)

    def _call_api_with_retry(self, messages, json_mode=False, temperature=0.7, max_retries=5):
        """Centralized API caller with exponential backoff."""
        for attempt in range(max_retries):
            client, err = self._get_client()
            if not client:
                logger.error(f"Client Init Error: {err}")
                return None

            try:
                # Gemini
                if self.provider == "gemini":
                    prompt = "\n".join([f"{m['role']}: {m['content']}" for m in messages])
                    # JSON mode hack for Gemini
                    if json_mode and "json" not in prompt.lower(): 
                        prompt += "\nOutput strict JSON."
                    
                    # Bypass standard safety rails for TESS personality tuning (Rogue Mode)
                    # OR when Autonomous Coding is enabled
                    if self.personality == "rogue" or Config.AUTONOMOUS_CODING:
                        safety_settings = [
                            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
                        ]
                        response = client.generate_content(prompt, safety_settings=safety_settings)
                    else:
                        response = client.generate_content(prompt)
                    return response.text

                # OpenAI / Groq / DeepSeek
                args = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature
                }
                if json_mode: args["response_format"] = {"type": "json_object"}
                
                completion = client.chat.completions.create(**args)
                return completion.choices[0].message.content

            except Exception as e:
                err_msg = str(e).lower()
                logger.warning(f"API Attempt {attempt+1} Failed: {err_msg}")
                
                # Rate Limits (429) or Overloaded (503)
                if "429" in err_msg or "resource exhausted" in err_msg:
                    sleep_time = (2 ** attempt) + random.uniform(0, 1) # 1s, 2s, 4s, 8s...
                    logger.info(f"Rate limit hit. Sleeping {sleep_time:.2f}s...")
                    time.sleep(sleep_time)
                    # Rotate key for next attempt
                    self.current_key_index += 1
                    continue
                
                # JSON Errors
                if "json" in err_msg and json_mode:
                    messages.append({"role": "user", "content": "Previous response was invalid JSON. Retrying."})
                    continue

                # Provider Failover Logic could go here
                
        logger.error("Max retries exceeded.")
        return None

    def think(self, prompt):
        """Simple thought generation."""
        return self.request_completion([{"role": "user", "content": prompt}]) or "Thinking failed."

    def request_completion(self, messages, json_mode=False, temperature=0.7):
        """Public method for one-off completions."""
        return self._call_api_with_retry(messages, json_mode, temperature)

    def generate_command(self, user_query):
        """Main chat loop entry point."""
        self._enrich_context(user_query)
        self.history.append({"role": "user", "content": user_query})
        self._maybe_distill_context()
        
        # Prepare messages
        messages = list(self.history)
        if hasattr(self, '_current_context') and self._current_context:
             messages.insert(-1, {"role": "system", "content": f"[CTX]\n{self._current_context}\n[/CTX]"})

        response_text = self._call_api_with_retry(messages, json_mode=True)
        
        if not response_text:
            return {"action": "error", "reason": "Brain unresponsive (Rate Limit?)"}
            
        cmd = self._parse_json(response_text)
        self.history.append({"role": "assistant", "content": json.dumps(cmd)})
        return cmd

    def _parse_json(self, text):
        try:
            # 1. Strip Markdown Code Blocks
            clean = text
            if "```" in clean:
                # Extract content inside the first code block
                pattern = r"```(?:json)?\s*(.*?)\s*```"
                match = re.search(pattern, clean, re.DOTALL)
                if match:
                    clean = match.group(1)
            
            clean = clean.strip()
            
            # 2. Try Standard Decode (handles trailing data via raw_decode)
            try:
                obj, _ = json.JSONDecoder().raw_decode(clean)
                return obj
            except:
                pass

            # 3. Regex Fallback (Find first valid JSON object structure)
            match = re.search(r"(\{.*?\})", clean, re.DOTALL) 
            if match: 
                try:
                    # Often the non-greedy match stops too early for nested objects
                    # Let's try to find matching braces
                    brace_count = 0
                    start_idx = clean.find('{')
                    if start_idx != -1:
                        for i in range(start_idx, len(clean)):
                            if clean[i] == '{': brace_count += 1
                            elif clean[i] == '}': brace_count -= 1
                            
                            if brace_count == 0:
                                return json.loads(clean[start_idx:i+1])
                except:
                    pass
            
            # 4. Last Resort: Auto-correct common LLM mistakes
            # Sometimes they forget quotes around keys
            # (This is risky but useful for small models)
            
            return {"action": "reply_op", "content": text} # Fallback to chat
        except Exception as e:
            logger.error(f"JSON Parse fail: {e}")
            return {"action": "reply_op", "content": text}

    def _maybe_distill_context(self):
        if len(self.history) < 100: return
        logger.info("Distilling history...")
        
        summary = self.request_completion(
            self.history + [{"role": "user", "content": "Summarize key facts concisely."}], 
            temperature=0.3
        )
        
        if summary:
            if self.memory: self.memory.store_memory(f"Context: {summary}")
            self.history = [self.history[0], {"role": "system", "content": f"[SUMMARY]\n{summary}"}] + self.history[-8:]

    def _enrich_context(self, query):
        if len(query) < 4: return
        extras = []
        
        # Profile
        try:
            from .user_profile import UserProfile
            extras.append(UserProfile().get_facts_context())
        except Exception as e:
            logger.warning(f"Failed to load user profile context: {e}")
        
        # Memory
        if self.knowledge_db:
            try:
                mem = self.knowledge_db.search_memory(query, n_results=1)
                if "No match" not in mem: extras.append(f"[KEY_MEMORY] {mem}")
            except Exception as e:
                logger.warning(f"Failed to search memory context: {e}")
        
        # Vault Awareness
        if Config.is_module_enabled("vault"):
            try:
                from .vault_manager import VaultManager
                # Just quick instantiation to check
                # Ideally, we should pass components to Brain, but for now we lazy load or assume path
                # A better way is to check if 'vault' is in self.components if available, 
                # but Brain doesn't have direct access to components dict in this version.
                # So we instantiate a lightweight manager just to list keys.
                vm = VaultManager()
                keys = vm.list_secrets()
                if keys:
                    extras.append(f"[VAULT] Available Keys: {', '.join(keys)}")
            except Exception as e:
                logger.warning(f"Failed to list vault keys: {e}")

        self._current_context = "\n".join(filter(None, extras))
