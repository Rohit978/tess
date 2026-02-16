"""
TESS Agentic Loop - Multi-step Reasoning & Execution
Enables TESS to loop through multiple actions to solve complex tasks.
"""
import time
from .terminal_ui import print_thinking, clear_thinking, print_tess_action, print_error, print_info, print_warning
from .orchestrator import process_action
from .config import Config

class AgenticLoop:
    def __init__(self, brain, components, max_steps=10):
        self.brain = brain
        self.components = components
        self.max_steps = max_steps

    def run(self, user_query):
        """Execute a recursive loop of thinking and acting."""
        current_step = 0
        
        # Inject "Agentic Developer" persona into memory for this session
        self.brain.update_history("system", "You are now in AGENT MODE. Use the available tools recursively to solve the task. Provide a 'final_reply' only when completely finished.")

        while current_step < self.max_steps:
            current_step += 1
            if Config.get_ui_mode() == "minimal":
                print_thinking("Thinking...")
            else:
                print_thinking(f"Agent Step {current_step}/{self.max_steps}...")
            
            try:
                # 1. Ask Brain for next step
                response = self.brain.generate_command(user_query if current_step == 1 else "Continue working on the task.")
                clear_thinking()

                # --- ROBUST PARSING ---
                if isinstance(response, list):
                    response = response[0] if response and isinstance(response[0], dict) else {"action": "reply_op", "content": str(response)}
                elif not isinstance(response, dict):
                    response = {"action": "reply_op", "content": str(response)}
                # ----------------------

                # 🛡️ HUMANIZATION: Print 'thought' if available
                thought = response.get("thought")
                if thought:
                    from .terminal_ui import print_thought
                    print_thought(thought)

                action = response.get("action")
                
                # 2. SECURITY CHECK 🛡️
                security = self.components.get('security')
                if security:
                    is_safe, reason = security.validate_action(response)
                    if not is_safe:
                        from .terminal_ui import print_security_block
                        print_security_block(reason)
                        self.brain.update_history("system", f"Action BLOCKED by Security Engine: {reason}")
                        # Don't break! Let the brain try a different (safer) action.
                        user_query = f"The previous action was BLOCKED by your internal security policy. Reason: {reason}. Please propose a safer alternative."
                        continue

                # 3. Check for completion signal
                if action == "final_reply" or action == "reply_op":
                    process_action(response, self.components, self.brain)
                    break

                # 3. Execute action
                print_tess_action(f"Executing {action}...")
                res = process_action(response, self.components, self.brain)
                
                # Update query for next step
                user_query = f"The previous action '{action}' returned: {res}. What is the next step? (Or provide 'final_reply' if finished)"
                
                # Small delay to prevent runaway
                time.sleep(0.5)

            except Exception as e:
                clear_thinking()
                print_error(f"Agent Loop Error: {e}")
                break
        
        if current_step >= self.max_steps:
            print_info("Reached maximum agent steps. Task might be incomplete.")
