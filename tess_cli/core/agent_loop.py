import time
from .terminal_ui import print_thinking, clear_thinking, print_tess_action, print_error, print_info
from .orchestrator import process_action
from .config import Config

class AgenticLoop:
    """
    Manages the multi-step reasoning capabilities of TESS.
    """
    def __init__(self, brain, components, max_steps=10):
        self.brain = brain
        self.components = components
        self.max_steps = max_steps

    def run(self, user_query):
        current_step = 0
        
        # System instruction for agent mode
        sys_prompt = "MODE: AGENT. Use tools recursively. Output 'final_reply' when done."
        if not self.brain.history or self.brain.history[-1].get("content") != sys_prompt:
            self.brain.update_history("system", sys_prompt)
        
        while current_step < self.max_steps:
            current_step += 1
            print_thinking(f"Step {current_step}..." if Config.get_ui_mode() != "minimal" else "Thinking...")
            
            try:
                # Get next action
                input_msg = user_query if current_step == 1 else "Continue."
                response = self.brain.generate_command(input_msg)
                clear_thinking()

                # Parse
                if isinstance(response, list): response = response[0]
                if not isinstance(response, dict):
                    response = {"action": "reply_op", "content": str(response)}

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
                        self.brain.update_history("system", f"BLOCKED: {reason}")
                        continue

                # Execute
                terminal_actions = ["final_reply", "reply_op", "whatsapp_op", "youtube_op", "broadcast_op", "instagram_op"]
                if action in terminal_actions:
                    if action not in ["final_reply", "reply_op"]:
                        print_tess_action(f"Executing {action}...")
                    process_action(response, self.components, self.brain)
                    break

                print_tess_action(f"Executing {action}...")
                res = process_action(response, self.components, self.brain)
                
                user_query = f"Result of {action}: {res}. Next?"
                time.sleep(0.5)

            except Exception as e:
                clear_thinking()
                print_error(f"Agent Loop Error: {e}")
                break
