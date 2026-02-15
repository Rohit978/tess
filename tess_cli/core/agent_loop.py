"""
TESS Agentic Loop - Multi-step Reasoning & Execution
Enables TESS to loop through multiple actions to solve complex tasks.
"""
import time
from .terminal_ui import print_thinking, clear_thinking, print_tess_action, print_error, print_info
from .orchestrator import process_action

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
                if action == "final_reply":
                    process_action(response, self.components, self.brain)
                    break

                # 3. Execute action
                print_tess_action(f"Step {current_step}: Executing {action}...")
                res = process_action(response, self.components, self.brain)
                
                # 🛡️ SELF-HEALING: If step failed, prompt brain specifically for fix
                if "ERROR" in str(res).upper() or "[STDERR]" in str(res).upper():
                    print_warning(f"⚠️ Action failed. Initiating self-healing...")
                    
                    # Check if it's an UNKNOWN COMMAND
                    researcher = self.components.get('researcher')
                    err_str = str(res).lower()
                    unknown_indicators = ["not recognized", "not found", "is not a cmdlet", "is not a function"]
                    
                    if researcher and any(x in err_str for x in unknown_indicators):
                         # Try to extract the command name
                         # Simple regex to find what's usually after 'The term' or before 'is not recognized'
                         import re
                         match = re.search(r"'(.*?)' is not recognized", err_str) or re.search(r"term '(.*?)'", err_str)
                         cmd_name = match.group(1) if match else action
                         
                         research_result = researcher.research_command(cmd_name)
                         print_info(f"🔎 {research_result}")
                         user_query = f"I've researched the unknown command '{cmd_name}'. {research_result}. Now, try to fix your previous command or use an alternative."
                    else:
                        user_query = f"The previous action '{action}' failed with error: {res}. Please analyze the error and try a DIFFERENT approach or fix the command. You have {self.max_steps - current_step} steps left."
                else:
                    user_query = "Continue working on the task. Provide 'final_reply' if finished."
                
                # Small delay to prevent runaway
                time.sleep(0.5)

            except Exception as e:
                clear_thinking()
                print_error(f"Agent Loop Error: {e}")
                break
        
        if current_step >= self.max_steps:
            print_info("Reached maximum agent steps. Task might be incomplete.")
