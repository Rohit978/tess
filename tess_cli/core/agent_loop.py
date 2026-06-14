import time
from .terminal_ui import print_thinking, clear_thinking, print_tess_action, print_error, print_info
from .orchestrator import process_action
from .config import Config

class AgenticLoop:
    """
    Manages the multi-step reasoning capabilities of TESS.
    """
    # All recognized action types — anything outside this set is an LLM hallucination
    KNOWN_ACTIONS = {
        "reply_op", "final_reply", "error",
        "execute_command", "launch_app", "system_control", "sysadmin_op",
        "web_search_op", "web_op", "file_op", "code_op",
        "youtube_op", "whatsapp_op", "broadcast_op", "instagram_op",
        "desktop_vision_op", "dom_op", "hearing_op", "os_op",
        "design_op", "pdf_op", "converter_op",
        "gmail_op", "calendar_op", "vault_op", "memory_op", "git_op",
        "planner_op", "run_skill", "teach_skill", "coding_mode_op",
        "presentation_op", "pentest_op", "rag_op", "review_op",
        "experimental_op", "trip_planner_op", "screencast_op",
    }

    def __init__(self, brain, components, max_steps=10, max_replans=3):
        self.brain = brain
        self.components = components
        self.max_steps = max_steps
        self.max_replans = max_replans
        self.last_reflections = []

    def _validate_action_payload(self, action_data):
        if not isinstance(action_data, dict):
            return False, "Response is not a JSON object."

        action = action_data.get("action")
        if not action:
            return False, "Missing 'action' field."

        # Guard: LLM sometimes returns nested objects instead of a string action
        if not isinstance(action, str):
            action_data["action"] = "reply_op"
            action_data.setdefault("content", str(action))
            return True, "Coerced non-string action to reply_op."

        # Guard: Coerce unknown/hallucinated action names to reply_op
        # Check both the hardcoded set AND the dynamic skill registry
        skill_registry = self.components.get("skill_registry", {})
        if action not in self.KNOWN_ACTIONS and action not in skill_registry:
            # Salvage conversational content: scan ALL string values, pick the longest
            # The LLM uses random field names like 'greeting', 'response_text', 'output', etc.
            skip_keys = {"action", "thought"}
            best = ""
            for k, v in action_data.items():
                if k in skip_keys or not isinstance(v, str):
                    continue
                if len(v) > len(best):
                    best = v
            # Fall back to thought if no content found anywhere else
            if not best:
                best = action_data.get("thought", "")
            action_data["action"] = "reply_op"
            action_data["content"] = best
            return True, f"Coerced unknown action '{action}' to reply_op."

        required_fields = {
            "execute_command": ["command", "content"],
            "reply_op": ["content"],
            "final_reply": ["content"],
            "launch_app": ["app_name", "content"],
            "web_search_op": ["query", "content"],
            "web_op": ["url", "content"],
            "file_op": ["sub_action", "path"],
            "code_op": ["sub_action"],
            "system_control": ["sub_action"],
            "sysadmin_op": ["sub_action"],
            "youtube_op": ["sub_action", "query"],
            "whatsapp_op": ["sub_action", "contact", "message"],
            "desktop_vision_op": ["sub_action"],
            "dom_op": ["sub_action"],
            "hearing_op": ["sub_action"],
        }

        required = required_fields.get(action)
        if required and not all(k in action_data for k in required):
            # Accept if at least one of the alternatives is present for multi-key options.
            if action in ["execute_command", "launch_app", "web_search_op", "web_op", "youtube_op", "whatsapp_op"]:
                if not any(action_data.get(k) for k in required):
                    return False, f"Action '{action}' missing required payload."
            else:
                missing = [k for k in required if k not in action_data]
                if missing:
                    return False, f"Action '{action}' missing keys: {', '.join(missing)}"

        return True, "Action payload valid."

    def _result_suggests_failure(self, result):
        import re
        text = str(result).lower()
        failure_patterns = [
            r'\berror\b', r'\bfailed\b', r'\btimed out\b',
            r'\bnot found\b', r'\bblocked\b', r'\bunavailable\b',
            r'\bdisabled\b',
        ]
        return any(re.search(p, text) for p in failure_patterns)

    def run(self, user_query):
        original_query = user_query  # Preserve original intent; never mutate this
        current_step = 0
        replans = 0
        reflections = []
        
        # System instruction for agent mode
        sys_prompt = (
            "MODE: AGENT-PLANNER. For each step: plan briefly, execute one best action, "
            "reflect on result, then decide next action. Output 'final_reply' when done."
        )
        if not self.brain.history or self.brain.history[-1].get("content") != sys_prompt:
            self.brain.update_history("system", sys_prompt)
        
        while current_step < self.max_steps:
            current_step += 1
            print_thinking(f"Step {current_step}..." if Config.get_ui_mode() != "minimal" else "Thinking...")
            
            try:
                # Get next action
                if current_step == 1:
                    input_msg = user_query
                else:
                    latest_reflection = reflections[-1] if reflections else "No prior issues."
                    input_msg = (
                        f"Original goal: {original_query}. "
                        "Continue the task. "
                        f"Latest reflection: {latest_reflection} "
                        "If previous action failed, choose a different strategy."
                    )
                response = self.brain.generate_command(input_msg)
                clear_thinking()

                # Parse
                if isinstance(response, list): response = response[0] if response else {"action": "reply_op", "content": "I couldn't generate a response."}
                if not isinstance(response, dict):
                    response = {"action": "reply_op", "content": str(response)}

                valid, reason = self._validate_action_payload(response)
                if not valid:
                    replans += 1
                    reflection = f"Invalid action payload at step {current_step}: {reason}"
                    reflections.append(reflection)
                    self.brain.update_history("system", f"REFLECT: {reflection}")
                    if replans > self.max_replans:
                        print_error("Agent stopped: too many invalid plans.")
                        break
                    continue

                # UI: Show Thought
                if response.get("thought"):
                    from .terminal_ui import print_thought
                    print_thought(response["thought"])

                action = response.get("action")
                
                # Security
                security = self.components.get('security')
                if security:
                    safe, reason = security.validate_action(response)
                    if not safe:
                        from .terminal_ui import print_security_block
                        print_security_block(reason)
                        replans += 1
                        reflection = f"Security blocked action '{action}': {reason}"
                        reflections.append(reflection)
                        self.brain.update_history("system", f"BLOCKED: {reason}. Choose a safer alternative.")
                        if replans > self.max_replans:
                            print_error("Agent stopped: too many blocked plans.")
                            break
                        continue

                # Execute terminal actions (after security check above)
                terminal_actions = ["final_reply", "reply_op", "whatsapp_op", "youtube_op", "broadcast_op", "instagram_op"]
                if action in terminal_actions:
                    # Guard: if reply content is empty, re-try instead of printing a blank bubble
                    if action in ("reply_op", "final_reply") and not (response.get("content") or "").strip():
                        replans += 1
                        self.brain.update_history(
                            "system",
                            "Your last response had empty content. Reply using: "
                            '{"action": "reply_op", "content": "your message here"}'
                        )
                        if replans > self.max_replans:
                            print_error("Agent stopped: too many empty replies.")
                            break
                        continue
                    if action not in ["final_reply", "reply_op"]:
                        print_tess_action(f"Executing {action}...")
                    process_action(response, self.components, self.brain)
                    break

                print_tess_action(f"Executing {action}...")
                res = process_action(response, self.components, self.brain)

                if self._result_suggests_failure(res):
                    replans += 1
                    reflection = f"Execution failure after '{action}': {res}"
                    reflections.append(reflection)
                    self.brain.update_history(
                        "system",
                        f"REFLECT: Last action failed ({action}). Error={res}. Try a different approach."
                    )
                    if replans > self.max_replans:
                        print_error("Agent stopped: too many failed executions.")
                        break
                else:
                    # Feed result back as context without mutating the original query
                    self.brain.update_history("system", f"Result of {action}: {str(res)[:500]}")
                    reflections.append(f"Completed '{action}' successfully.")
                time.sleep(0.5)

            except Exception as e:
                clear_thinking()
                print_error(f"Agent Loop Error: {e}")
                break

        self.last_reflections = reflections
