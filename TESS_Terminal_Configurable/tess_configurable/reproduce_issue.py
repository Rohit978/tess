import sys
import os
import traceback

# Ensure we can import tess_configurable
sys.path.append(os.getcwd())

try:
    from tess_configurable.core.orchestrator import Orchestrator
    from tess_configurable.config_manager import get_config_manager
    from tess_configurable.core.brain import Brain
except ImportError as e:
    print(f"Import Error: {e}")
    sys.exit(1)

# Mock Brain
class MockBrain:
    def __init__(self):
        pass
    def generate_command(self, text):
        return {}
    def think(self, text):
        return {}

def mock_output(text):
    print(f"[OUTPUT] {text}")

def main():
    print("Starting reproduction...")
    try:
        # Load config
        cm = get_config_manager()
        print("Config loaded.")
        
        # Initialize Orchestrator
        orc = Orchestrator(cm.config)
        print("Orchestrator initialized.")
        
        # Mock components if needed
        # whatsapp_client is lazy loaded in _handle_whatsapp
        
        # Define action that causes crash
        action = {
            "action": "whatsapp_op", 
            "sub_action": "chat", 
            "contact": "Siddharth Singh", 
            "reason": "Test Reproduction"
        }
        
        print(f"Processing action: {action}")
        
        # Process action
        # We need to pass valid components dict? Orchestrator initializes them inside __init__?
        # No, Orchestrator.__init__ creates self.components = {}
        # And lazily loads them.
        
        orc.process_action(action, orc.components, MockBrain(), mock_output)
        print("Success! No error.")
        
    except Exception as e:
        print(f"\nCRITICIAL FAILURE CAUGHT: {type(e).__name__}: {e}")
        print("Traceback:")
        traceback.print_exc()

if __name__ == "__main__":
    main()
