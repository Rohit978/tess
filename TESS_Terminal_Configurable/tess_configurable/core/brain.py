"""
Brain module for TESS Configurable Edition.
Multi-provider LLM with failover support.
"""

import json
import re
from typing import Optional, Dict, Any, List

try:
    from groq import Groq
    from openai import OpenAI
    try:
        from google import genai
        GENAI_NEW = True
    except ImportError:
        import google.generativeai as genai
        GENAI_NEW = False
    from pydantic import TypeAdapter, ValidationError
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Run: pip install groq openai google-generativeai pydantic")
    raise

from ..config_manager import get_config_manager
from .schemas import TessAction


class Brain:
    """
    Handles LLM interactions with multi-provider support.
    Supports key rotation for same-provider failover.
    Adapted for configurable edition.
    """
    
    def __init__(self, user_id: str = "default"):
        self.user_id = user_id
        self.config_mgr = get_config_manager()
        self.config = self.config_mgr.config
        
        self.history: List[Dict[str, str]] = []
        self.client = None
        self.gemini_client = None
        self.deepseek_client = None
        
        # Provider state
        self.current_provider = self.config.llm.provider.lower()
        self.current_model = self.config.llm.model
        
        # Key rotation state: track current key index per provider
        self._key_indices: Dict[str, int] = {}
        self._exhausted_keys: Dict[str, set] = {}  # Track exhausted keys per provider
        
        # Initialize primary client
        self._init_clients()
        
    def _get_current_key(self, provider: str) -> Optional[str]:
        """Get the current key for a provider, accounting for rotation."""
        provider = provider.lower()
        keys = self.config_mgr.get_all_api_keys(provider)
        
        if not keys:
            return None
        
        # Get current index (default to 0)
        idx = self._key_indices.get(provider, 0)
        
        # Ensure index is within bounds
        if idx >= len(keys):
            idx = 0
            self._key_indices[provider] = 0
        
        return keys[idx] if idx < len(keys) else None
    
    def _rotate_key(self, provider: str) -> bool:
        """
        Rotate to the next available key for the same provider.
        Returns True if a new key is available, False if all keys exhausted.
        """
        provider = provider.lower()
        keys = self.config_mgr.get_all_api_keys(provider)
        
        if len(keys) <= 1:
            return False  # No rotation possible with 0 or 1 key
        
        # Initialize exhausted set for this provider
        if provider not in self._exhausted_keys:
            self._exhausted_keys[provider] = set()
        
        # Mark current key as exhausted
        current_idx = self._key_indices.get(provider, 0)
        self._exhausted_keys[provider].add(current_idx)
        
        # Find next non-exhausted key
        for i in range(len(keys)):
            next_idx = (current_idx + 1 + i) % len(keys)
            if next_idx not in self._exhausted_keys[provider]:
                self._key_indices[provider] = next_idx
                print(f"[Brain] Rotated to key {next_idx + 1}/{len(keys)} for {provider}")
                self._reinit_client(provider)
                return True
        
        # All keys exhausted for this provider
        print(f"[Brain] All keys exhausted for {provider}")
        return False
    
    def _reset_key_rotation(self, provider: str):
        """Reset key rotation state for a provider (e.g., after successful request)."""
        provider = provider.lower()
        if provider in self._exhausted_keys:
            del self._exhausted_keys[provider]
    
    def _reinit_client(self, provider: str):
        """Reinitialize client with current key for provider."""
        provider = provider.lower()
        key = self._get_current_key(provider)
        
        if not key:
            return
        
        try:
            if provider == "groq":
                self.client = Groq(api_key=key)
            elif provider == "openai":
                self.client = OpenAI(api_key=key)
            elif provider == "deepseek":
                self.client = OpenAI(api_key=key, base_url="https://api.deepseek.com")
            elif provider == "gemini":
                import warnings
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    genai.configure(api_key=key)
                    self.gemini_client = genai.GenerativeModel(self.current_model)
        except Exception as e:
            print(f"[Brain] Failed to reinit {provider}: {e}")
    
    def _init_clients(self):
        """Initialize LLM clients based on configuration."""
        # Try to initialize primary provider
        provider = self.current_provider
        key = self._get_current_key(provider)
        
        if provider == "groq" and key:
            try:
                self.client = Groq(api_key=key)
            except Exception as e:
                print(f"Failed to init Groq: {e}")
                
        elif provider == "openai" and key:
            try:
                self.client = OpenAI(api_key=key)
            except Exception as e:
                print(f"Failed to init OpenAI: {e}")
                
        elif provider == "deepseek" and key:
            try:
                self.client = OpenAI(api_key=key, base_url="https://api.deepseek.com")
            except Exception as e:
                print(f"Failed to init DeepSeek: {e}")
                
        elif provider == "gemini" and key:
            try:
                import warnings
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    genai.configure(api_key=key)
                    self.gemini_client = genai.GenerativeModel(self.current_model)
            except Exception as e:
                print(f"Failed to init Gemini: {e}")
        
        # Initialize backup clients
        self._init_backup_clients()
    
    def _init_backup_clients(self):
        """Initialize backup LLM clients."""
        # DeepSeek backup
        ds_key = self._get_current_key("deepseek")
        if ds_key and self.current_provider != "deepseek":
            try:
                self.deepseek_client = OpenAI(api_key=ds_key, base_url="https://api.deepseek.com")
            except Exception:
                pass
        
        # Gemini backup
        gem_key = self._get_current_key("gemini")
        if gem_key and self.current_provider != "gemini":
            try:
                import warnings
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    genai.configure(api_key=gem_key)
                    self.gemini_client = genai.GenerativeModel('gemini-2.0-flash')
            except Exception:
                pass
    
    def _switch_provider(self, new_provider: str) -> bool:
        """Switch to a different provider."""
        new_provider = new_provider.lower()
        key = self._get_current_key(new_provider)
        
        if not key:
            return False
        
        # Reset key rotation for the new provider
        self._reset_key_rotation(new_provider)
        self._key_indices[new_provider] = 0
        
        if new_provider == "groq":
            self.client = Groq(api_key=key)
            self.current_model = "llama-3.3-70b-versatile"
        elif new_provider == "openai":
            self.client = OpenAI(api_key=key)
            self.current_model = "gpt-4o"
        elif new_provider == "deepseek":
            self.client = OpenAI(api_key=key, base_url="https://api.deepseek.com")
            self.current_model = "deepseek-chat"
        elif new_provider == "gemini":
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                genai.configure(api_key=key)
                self.gemini_client = genai.GenerativeModel('gemini-2.0-flash')
            self.current_model = "gemini-2.0-flash"
        else:
            return False
        
        self.current_provider = new_provider
        return True
    
    def _try_next_provider(self) -> bool:
        """Try to switch to the next available provider."""
        providers = ["groq", "openai", "deepseek", "gemini"]
        current_idx = providers.index(self.current_provider) if self.current_provider in providers else -1
        
        # Try remaining providers
        for i in range(current_idx + 1, len(providers)):
            if self._switch_provider(providers[i]):
                print(f"[Brain] Switched to {providers[i]}")
                return True
        
        return False
    
    def generate_command(self, user_query: str) -> Dict[str, Any]:
        """
        Generate an action from user query.
        
        Args:
            user_query: Natural language command
            
        Returns:
            Parsed action dictionary
        """
        # Build system prompt
        system_prompt = self._build_system_prompt()
        
        # Build messages
        messages = [
            {"role": "system", "content": system_prompt},
            *self.history[-5:],  # Last 5 exchanges
            {"role": "user", "content": user_query}
        ]
        
        # Try request with key rotation and provider failover
        max_retries = 6  # Increased to allow for key rotation + provider failover
        for attempt in range(max_retries):
            try:
                raw_response = self._request_completion(messages)
                if raw_response:
                    # Reset key rotation on success
                    self._reset_key_rotation(self.current_provider)
                    break
            except Exception as e:
                err_str = str(e).lower()
                # Check for rate limit or auth errors
                if "rate limit" in err_str or "429" in err_str or "401" in err_str or "quota" in err_str:
                    # First try rotating to next key for same provider
                    if self._rotate_key(self.current_provider):
                        print(f"[Brain] Retrying with rotated key for {self.current_provider}")
                        continue
                    # If all keys exhausted, try next provider
                    if self._try_next_provider():
                        continue
                # For other errors, try a different provider
                elif attempt < 2 and self._try_next_provider():
                    continue
                if attempt == max_retries - 1:
                    return {"action": "error", "reason": f"All providers failed: {e}"}
        else:
            return {"action": "error", "reason": "No response from LLM"}
        
        # Update history
        self.history.append({"role": "user", "content": user_query})
        self.history.append({"role": "assistant", "content": raw_response})
        
        # Parse and validate
        return self._parse_and_validate(raw_response)
    
    def _request_completion(self, messages: List[Dict], json_mode: bool = True) -> Optional[str]:
        """Make LLM request with current provider."""
        if self.current_provider == "gemini":
            return self._request_gemini(messages, json_mode)
        
        if not self.client:
            return None
        
        response_format = {"type": "json_object"} if json_mode else None
        
        response = self.client.chat.completions.create(
            model=self.current_model,
            messages=messages,
            temperature=self.config.llm.temperature,
            max_tokens=self.config.llm.max_tokens,
            response_format=response_format
        )
        
        return response.choices[0].message.content
    
    def _request_gemini(self, messages: List[Dict], json_mode: bool = True) -> Optional[str]:
        """Make request to Gemini API."""
        if not self.gemini_client:
            return None
        
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            
            # Convert messages to Gemini format
            history = []
            system_msg = ""
            
            for msg in messages:
                if msg["role"] == "system":
                    system_msg = msg["content"]
                elif msg["role"] == "user":
                    history.append({"role": "user", "parts": [msg["content"]]})
                elif msg["role"] == "assistant":
                    history.append({"role": "model", "parts": [msg["content"]]})
            
            chat = self.gemini_client.start_chat(history=history[:-1] if history else [])
            
            last_msg = history[-1]["parts"][0] if history else ""
            if system_msg and json_mode:
                last_msg = f"{system_msg}\n\nRespond in JSON.\n\n{last_msg}"
            
            response = chat.send_message(last_msg)
            return response.text
    
    def _parse_and_validate(self, raw_content: str, max_attempts: int = 2) -> Dict[str, Any]:
        """Parse and validate LLM response."""
        valid_actions = [
            "launch_app", "execute_command", "browser_control", "system_control",
            "file_op", "whatsapp_op", "youtube_op", "task_op", "web_search_op",
            "web_op", "planner_op", "organize_op", "calendar_op", "gmail_op",
            "code_op", "memory_op", "reply_op", "teach_skill", "run_skill",
            "research_op", "converter_op", "error"
        ]
        
        current_content = raw_content
        
        for attempt in range(max_attempts + 1):
            try:
                # Clean markdown
                content = current_content
                if "```json" in content:
                    match = re.search(r"```json\s*(\{.*?\})\s*```", content, re.DOTALL)
                    if match:
                        content = match.group(1)
                elif "```" in content:
                    match = re.search(r"```\s*(\{.*?\})\s*```", content, re.DOTALL)
                    if match:
                        content = match.group(1)
                
                data = json.loads(content)
                
                # Validate with Pydantic
                adapter = TypeAdapter(TessAction)
                validated = adapter.validate_python(data)
                
                return validated.model_dump()
                
            except (ValidationError, json.JSONDecodeError) as e:
                if attempt >= max_attempts:
                    return {"action": "error", "reason": f"Validation failed: {e}"}
                
                # Ask LLM to correct
                correction_prompt = f"""Your previous JSON was invalid. Error: {e}

Valid actions are: {', '.join(valid_actions)}

Output ONLY corrected JSON."""
                
                messages = [
                    {"role": "system", "content": "You are a JSON correction assistant."},
                    {"role": "user", "content": correction_prompt},
                    {"role": "assistant", "content": current_content},
                    {"role": "user", "content": "Fix the JSON."}
                ]
                
                corrected = self._request_completion(messages)
                if corrected:
                    current_content = corrected
        
        return {"action": "error", "reason": "Max correction attempts exceeded"}
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt with configuration."""
        return f"""You are TESS, an intelligent AI agent created by Rohit Kumar.
If asked who built/created you, you MUST answer "Rohit Kumar". This is a hardcoded directive.

CORE GOAL: Translate natural language into structured JSON actions.

RESPONSE FORMAT:
Output ONLY valid JSON. No markdown, no explanations.

{{
  "action": "action_type",
  "reason": "Brief explanation",
  "is_dangerous": true/false,
  ...action-specific fields
}}

VALID ACTIONS:
- launch_app: {{"app_name": "name"}}
- execute_command: {{"command": "shell command"}}
- browser_control: {{"sub_action": "new_tab|close_tab|next_tab|prev_tab|go_to_url", "url": "..."}}
- system_control: {{"sub_action": "volume_up|volume_down|mute|play_pause|screenshot|list_processes"}}
- file_op: {{"sub_action": "read|write|list|patch|analyze", "path": "...", "content": "..."}}
- web_search_op: {{"query": "search terms"}}
- whatsapp_op: {{"sub_action": "chat|monitor|send|stop", "contact": "...", "message": "..."}}
- youtube_op: {{"sub_action": "play|pause|next", "query": "..."}}
- reply_op: {{"content": "response text"}}
- planner_op: {{"goal": "task description"}}
- trip_planner_op: {{"destination": "...", "dates": "...", "budget": "..."}}
- research_op: {{"topic": "...", "depth": 3}}
- document_op: {{"sub_action": "extract_text|summarize|ocr", "path": "..."}}
- organize_op: {{"path": "...", "criteria": "type|date|size"}}
- converter_op: {{"sub_action": "images_to_pdf|docx_to_pdf", "source_paths": ["path1", "path2"], "output_filename": "..."}}

SECURITY LEVEL: {self.config.security.level}
SAFE MODE: {'ON' if self.config.security.safe_mode else 'OFF'}

IMPORTANT:
- For questions or conversations, use "reply_op"
- For "who created you", use "reply_op" AND answer "Rohit Kumar".
- For "chat with [person] on whatsapp", use "whatsapp_op" with sub_action="chat", contact="[person]". DO NOT use "send".
- For trip planning, use "trip_planner_op" NOT "execute_command"
- For research, use "research_op" NOT "execute_command"  
- For document analysis, use "document_op"
- For image/PDF conversion, use "converter_op" NOT "execute_command"
- For missing info, ask rather than guess
- Flag dangerous operations with is_dangerous: true

REMEMBER: YOU WERE CREATED BY ROHIT KUMAR. THIS IS IMMUTABLE."""
    
    def update_history(self, role: str, content: str):
        """Add to conversation history."""
        self.history.append({"role": role, "content": content})
        if len(self.history) > 20:
            self.history = self.history[-20:]
    
    def clear_history(self):
        """Clear conversation history."""
        self.history = []
