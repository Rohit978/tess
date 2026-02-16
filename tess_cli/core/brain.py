import json
import re
import os
import time
import warnings
# Suppress the specific FutureWarning from google-generativeai
warnings.filterwarnings("ignore", category=FutureWarning)
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
    
    def __init__(self, user_id="default", knowledge_db=None, personality="casual"):
        self.user_id = str(user_id)
        self.personality = personality
        self.history = [{"role": "system", "content": Config.get_system_prompt(personality)}]
        
        # Initialize Memory components
        self.memory = MemoryEngine(user_id=self.user_id)
        self.knowledge_db = knowledge_db 
        self.skill_manager = None # Injected later
        
        # Current State
        self.provider = Config.LLM_PROVIDER
        self.model = Config.LLM_MODEL
        self.current_key_index = 0
        logger.info(f"Brain Initialized | Provider: {self.provider.upper()} | Model: {self.model}")

    def _get_client(self, provider):
        """
        Get a client instance using the current key index for rotation.
        """
        key = Config.get_api_key(provider, index=self.current_key_index)
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

    def update_history(self, role, content):
        """Append a message to the conversation history."""
        self.history.append({"role": role, "content": content})

    def generate_command(self, user_query):

        """
        Generates a JSON command from user input.
        """
        # 1. Enrich Context (RAG, Skills, etc.)
        self._enrich_context(user_query)
        
        # 2. Update History
        self.history.append({"role": "user", "content": user_query})
        
        # 3. Context Distillation (Infinite Memory)
        self._maybe_distill_context()

        # 4. Request Completion
        return self._execute_llm_request()

    def _maybe_distill_context(self):
        """
        If history is too long, distill it into key facts and progress
        to prevent 'forgetting'.
        """
        if len(self.history) < 20:
             return

        logger.info("🧠 History too long. Distilling context...")
        
        # 1. Prepare Distillation Prompt
        summary_prompt = (
            "Summarize the conversation so far in a few bullet points. "
            "Focus on: 1. Discovered facts about the user. 2. Current project status. 3. Decisions made. "
            "KEEP IT CONCISE AND IN THIRD PERSON."
        )
        
        # We use a separate request so we don't mess with the history while distilling
        messages = self.history + [{"role": "user", "content": summary_prompt}]
        distilled = self.request_completion(messages, temperature=0.3)
        
        if distilled:
            # 2. Update Memory with the distillation
            if self.memory:
                self.memory.store_memory(f"Distilled Context: {distilled}")
            
            # 3. Trim History: Keep system prompt, distilled fact, and last 4 exchanges
            distilled_msg = {"role": "system", "content": f"[DISTILLED CONTEXT FROM PREVIOUS CHATS]\n{distilled}"}
            self.history = [self.history[0], distilled_msg] + self.history[-8:]
            logger.info("✅ Context distilled and history trimmed.")

    def _enrich_context(self, query):
        """Injects RAG, Skill, and User Profile context into the conversation."""
        extras = []
        
        # 0. GUARD: Skip RAG for simple greetings to prevent hallucination
        simple_queries = ["hey", "hello", "hi", "hey buddy", "yo", "tess", "are you there"]
        is_simple = query.lower().strip().strip("?!.") in simple_queries or len(query.strip()) < 3
        
        # User Profile Facts (Always helpful)
        try:
            from .user_profile import UserProfile
            profile = UserProfile()
            facts_ctx = profile.get_facts_context()
            if facts_ctx:
                extras.append(f"\n[USER PROFILE]\n{facts_ctx}")
        except: pass

        # Memory / Knowledge DB (Only for substantive queries)
        if self.knowledge_db and not is_simple:
            try:
                mem = self.knowledge_db.search_memory(query, n_results=1)
                if "No matching" not in mem:
                    extras.append(f"\n[MEMORY]\n{mem}")
                
                rag = self.knowledge_db.search(query, n_results=1)
                if "Command:" in rag:
                    extras.append(f"\n[DOCS]\n{rag}")
            except: pass

        # Skills (Always show available tools)
        if self.skill_manager:
            svs = self.skill_manager.list_skills()
            if svs: extras.append(f"\n[SKILLS] Available: {', '.join(svs)}")

        if extras:
             ctx = "\n".join(extras)
             # 🛡️ SANITIZE: Remove control characters (except newline/tab) that confuse some LLMs
             self._current_context = "".join(ch for ch in ctx if ch.isprintable() or ch in "\n\t")
        else:
             self._current_context = ""

    def _execute_llm_request(self, retry_count=0):
        """
        Central execution logic with Provider Failover and Key Rotation.
        """
        if retry_count > 4:
            return {"action": "error", "reason": "Max LLM Retries Exceeded. Please check your API keys."}

        # Get Client for current provider
        client, err = self._get_client(self.provider)
        if not client:
             # Missing key for current provider - try failover immediately
             if self.provider == "groq":
                 logger.warning("Groq key missing. Failing over to DeepSeek.")
                 self.provider = "deepseek"
                 self.model = "deepseek-coder"
                 return self._execute_llm_request(retry_count + 1)
             elif self.provider == "deepseek":
                 logger.warning("DeepSeek key missing. Failing over to Gemini.")
                 self.provider = "gemini"
                 self.model = "gemini-2.0-flash"
                 return self._execute_llm_request(retry_count + 1)
             return {"action": "error", "reason": f"Provider Error: {err}"}

        # Prepare Messages
        messages = list(self.history)
        
        # INJECT CONTEXT AS SYSTEM MESSAGE (Better adherence)
        if self._current_context:
            context_msg = {
                "role": "system", 
                "content": f"[ADDITIONAL CONTEXT]\n{self._current_context}\n[END CONTEXT]\nUse this context to answer the user, but DO NOT output it."
            }
            # Insert before the last user message
            if len(messages) > 0 and messages[-1]["role"] == "user":
                messages.insert(-1, context_msg)
            else:
                messages.append(context_msg)

        try:
            response_text = ""
            if self.provider in ["groq", "openai", "deepseek"]:
                completion = client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    response_format={"type": "json_object"},
                    stream=False
                )
                response_text = completion.choices[0].message.content
            elif self.provider == "gemini":
                prompt = "\n".join([f"{m['role']}: {m['content']}" for m in messages])
                resp = client.generate_content(prompt)
                response_text = resp.text

             # Parse - ROBUST JSON EXTRACTION
            try:
                # 1. Try direct clean first
                clean = response_text.replace("```json", "").replace("```", "").strip()
                cmd = json.loads(clean)
            except json.JSONDecodeError:
                # 2. Fallback: Extract first JSON object using Regex
                match = re.search(r"(\{.*\})", response_text, re.DOTALL)
                if match:
                    clean = match.group(1)
                    cmd = json.loads(clean)
                else:
                    raise ValueError(f"No JSON found in response: {response_text[:100]}...")

            self.history.append({"role": "assistant", "content": clean})
            return cmd

        except Exception as e:
            err_msg = str(e).lower()
            
            # Handle 400 (JSON Validation Failed) - RETRY WITH FORCE JSON
            # Even with regex, if it's malformed, we retry.
            if "400" in err_msg or "json" in err_msg or "valueerror" in err_msg:
                 logger.warning(f"JSON Parsing Failed ({e}). Retrying with strict enforcement...")
                 # Append a forceful system reminder/user tip to the END of messages
                 messages.append({"role": "user", "content": "PREVIOUS RESPONSE FAILED JSON VALIDATION. YOU MUST OUTPUT RAW JSON ONLY. NO TEXT. NO MARKDOWN."})
                 try:
                     # Retry ONCE with the same client
                     retry_completion = client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        response_format={"type": "json_object"},
                        stream=False
                     )
                     response_text = retry_completion.choices[0].message.content
                     clean = response_text.replace("```json", "").replace("```", "").strip()
                     cmd = json.loads(clean)
                     self.history.append({"role": "assistant", "content": clean})
                     return cmd
                 except Exception as final_e:
                     logger.error(f"Retry failed: {final_e}")
                     # let it fall through to main retry loop or return error
            
            # Handle 429 (Rate Limit) - IMMEDIATE FAILOVER
            if "429" in err_msg or "rate_limit_exceeded" in err_msg:
                 logger.warning(f"Rate Limit Exceeded for {self.provider}. Failing over immediately...")
                 if self.provider == "groq":
                     self.provider = "deepseek"
                     self.model = "deepseek-coder"
                 elif self.provider == "deepseek":
                     self.provider = "gemini"
                     self.model = "gemini-2.0-flash"
                 elif self.provider == "gemini":
                      # Last resort or cycle?
                      # For now, let it retry or fail if max reached.
                      pass
                 
                 return self._execute_llm_request(retry_count + 1)

            # Handle 401 (Auth) OR 404 (Model Not Found)
            if any(x in err_msg for x in ["401", "invalid api key", "404", "not found", "does not exist"]):
                # If it's a model error, maybe just switch model first?
                if "model" in err_msg:
                    if self.provider == "groq" and self.model != "llama3-8b-8192":
                        logger.warning(f"Groq Model {self.model} not found. Falling back to llama3-8b-8192.")
                        self.model = "llama3-8b-8192"
                        return self._execute_llm_request(retry_count + 1)
                    elif self.provider == "gemini" and self.model != "gemini-2.0-flash":
                        logger.warning(f"Gemini Model {self.model} not found/supported. Falling back to gemini-2.0-flash.")
                        self.model = "gemini-2.0-flash"
                        return self._execute_llm_request(retry_count + 1)

                # Get number of keys available for this provider
                num_keys = len(Config._data["llm"]["keys"].get(self.provider, []))
                
                if self.current_key_index < num_keys - 1:
                    # Move to the next key for the same provider
                    self.current_key_index += 1
                    logger.warning(f"Retrying {self.provider} with next available key (Index: {self.current_key_index})...")
                else:
                    # All keys for this provider failed, switch provider
                    self.current_key_index = 0 # Reset for next provider
                    if self.provider == "groq":
                        logger.warning("Groq consistently failing. Failing over to DeepSeek.")
                        self.provider = "deepseek"
                        self.model = "deepseek-coder"
                    elif self.provider == "deepseek":
                        logger.warning("DeepSeek consistently failing. Failing over to Gemini.")
                        self.provider = "gemini"
                        self.model = "gemini-2.0-flash"
            
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

    def request_completion(self, messages, json_mode=False, temperature=0.7):
        """
        Versatile completion request for non-standard flows (like WhatsApp).
        """
        client, _ = self._get_client(self.provider)
        if not client: return None
        
        try:
            if self.provider in ["groq", "openai", "deepseek"]:
                args = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature
                }
                if json_mode:
                    args["response_format"] = {"type": "json_object"}
                
                completion = client.chat.completions.create(**args)
                return completion.choices[0].message.content
            elif self.provider == "gemini":
                prompt = "\n".join([f"{m['role']}: {m['content']}" for m in messages])
                resp = client.generate_content(prompt)
                return resp.text
        except Exception as e:
            logger.error(f"Request Completion Failed: {e}")
            return None

