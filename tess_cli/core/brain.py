import json
import re
import os
import time
import warnings
warnings.filterwarnings("ignore", message=".*google.generativeai.*")
warnings.filterwarnings("ignore", category=FutureWarning, module="google.generativeai")
import google.generativeai as genai
from groq import Groq
from openai import OpenAI
from pydantic import TypeAdapter, ValidationError
from .config import Config
from .logger import setup_logger
from .memory_engine import MemoryEngine
from .schemas import TessAction

logger = setup_logger("Brain")

class Brain:
    """
    Handles LLM interactions using Config-driven Provider Switching & Key Rotation.
    Supports: Groq, OpenAI, DeepSeek, Gemini.
    """
    
    def __init__(self, user_id="default", knowledge_db=None):
        self.user_id = str(user_id)
        self.history = [{"role": "system", "content": Config.SYSTEM_PROMPT}]
        
        # Initialize Memory components
        self.memory = MemoryEngine(user_id=self.user_id)
        self.knowledge_db = knowledge_db 
        self.skill_manager = None # Injected later
        
        # Current State
        self.provider = Config.LLM_PROVIDER
        self.model = Config.LLM_MODEL
        logger.info(f"Brain Initialized | Provider: {self.provider.upper()} | Model: {self.model}")

    def _get_client(self, provider):
        """
        Get a client instance using a rotated key from Config.
        """
        key = Config.get_api_key(provider)
        if not key:
            return None, f"Missing API Key for {provider}"

        try:
            if provider == "groq":
                return Groq(api_key=key), None
            elif provider == "openai":
                return OpenAI(api_key=key), None
            elif provider == "deepseek":
                return OpenAI(api_key=key, base_url="https://api.deepseek.com"), None
            elif provider == "gemini":
                genai.configure(api_key=key)
                return genai.GenerativeModel(self.model), None
        except Exception as e:
            return None, str(e)
        return None, "Unknown Provider"

    def generate_command(self, user_query):
        """
        Generates a JSON command from user input.
        """
        # 1. Enrich Context (RAG, Skills, etc.)
        self._enrich_context(user_query)
        
        # 2. Update History
        self.history.append({"role": "user", "content": user_query})
        
        # 3. Sliding Window
        if len(self.history) > 12: # Keep system prompt + last 10
             self.history = [self.history[0]] + self.history[-10:]

        # 4. Request Completion
        return self._execute_llm_request()

    def _enrich_context(self, query):
        """Injects RAG and Skill context into the system prompt (simulated via msg injection)."""
        extras = []
        
        # Memory / Knowledge DB
        if self.knowledge_db:
            try:
                mem = self.knowledge_db.search_memory(query, n_results=1)
                if "No matching" not in mem:
                    extras.append(f"\n[MEMORY]\n{mem}")
                
                rag = self.knowledge_db.search(query, n_results=1)
                if "Command:" in rag:
                    extras.append(f"\n[DOCS]\n{rag}")
            except: pass

        # Skills
        if self.skill_manager:
            svs = self.skill_manager.list_skills()
            if svs: extras.append(f"\n[SKILLS] Available: {', '.join(svs)}")

        if extras:
            # We append ephemeral context to the last system message or strictly as a system msg
            # But to avoid messing with history too much, we just append it to the current user msg
             # Or better, update the System Prompt in history[0] temporarily? No, history[0] is static.
             pass 
             # For now, let's keep it simple. The previous implementation injected it into the prompt.
             # I will modify _execute_llm_request to prepend context to the immediate request messages.
             self._current_context = "\n".join(extras)
        else:
             self._current_context = ""

    def _execute_llm_request(self, retry_count=0):
        """
        Central execution logic with Provider Failover and Key Rotation.
        """
        if retry_count > 3:
            return {"action": "error", "reason": "Max LLM Retries Exceeded."}

        # Get Client for current provider
        client, err = self._get_client(self.provider)
        if not client:
             # Try failover?
             if self.provider == "groq":
                 logger.warning("Groq failed/missing. Switching to DeepSeek.")
                 self.provider = "deepseek"
                 self.model = "deepseek-coder"
                 return self._execute_llm_request(retry_count + 1)
             return {"action": "error", "reason": f"Provider Error: {err}"}

        # Prepare Messages (Inject context)
        messages = list(self.history)
        if self._current_context:
            # Inject context into the *last* user message or as a system message
            messages[-1]["content"] += f"\n\n{self._current_context}"

        try:
            response_text = ""
            
            # --- PROVIDER SPECIFIC CALLS ---
            if self.provider in ["groq", "openai", "deepseek"]:
                completion = client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    response_format={"type": "json_object"},
                    stream=False
                )
                response_text = completion.choices[0].message.content

            elif self.provider == "gemini":
                # Simplified Gemini call
                prompt = "\n".join([f"{m['role']}: {m['content']}" for m in messages])
                resp = client.generate_content(prompt)
                response_text = resp.text

            # --- PARSE AND RETURN ---
            # Clean markdown
            clean = response_text.replace("```json", "").replace("```", "").strip()
            
            try:
                cmd = json.loads(clean)
                self.history.append({"role": "assistant", "content": clean})
                return cmd
            except json.JSONDecodeError:
                # Self-Correction could go here
                return {"action": "reply_op", "content": f"JSON Error: {clean}"}

        except Exception as e:
            logger.error(f"LLM Call Failed ({self.provider}): {e}")
            # Rotation logic?
            # Config.get_api_key() returns random, so next call *might* use different key.
            # But we can force provider switch on specific errors.
            return self._execute_llm_request(retry_count + 1)

    def think(self, prompt):
        """Simple text-to-text for subtasks."""
        # Reuse _get_client logic or simplify
        client, _ = self._get_client(self.provider)
        if not client: return "LLM Error"
        
        try:
            if self.provider in ["groq", "openai", "deepseek"]:
                res = client.chat.completions.create(
                    model=self.model,
                    messages=[{"role":"user", "content": prompt}]
                )
                return res.choices[0].message.content
            elif self.provider == "gemini":
                return client.generate_content(prompt).text
        except:
            return "Thinking failed."
