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

                if not response or not isinstance(response, dict):
                    print_error("Failed to parse Agent response.")
                    break

                action = response.get("action")
                
                # 2. Check for completion signal
                if action == "final_reply":
                    process_action(response, self.components, self.brain)
                    break

                # 3. Execute action
                print_tess_action(f"Step {current_step}: Executing {action}...")
                # process_action already updates brain history with result
                res = process_action(response, self.components, self.brain)
                
                # Small delay to prevent runaway
                time.sleep(0.5)

            except Exception as e:
                clear_thinking()
                print_error(f"Agent Loop Error: {e}")
                break
        
        if current_step >= self.max_steps:
            print_info("Reached maximum agent steps. Task might be incomplete.")
