import sys
import os
import time
import traceback

sys.path.append(os.path.dirname(__file__))

# Fake brain object to satisfy dependency
class MockBrain:
    def __init__(self):
         self.history = []
    def update_history(self, role, msg):
         print(f"[BRAIN] {role}: {msg}")

def test():
    try:
        print("Importing WhatsAppClient...")
        from tess_cli.core.whatsapp_client import WhatsAppClient
        brain = MockBrain()
        client = WhatsAppClient(brain)
        
        print("Starting monitor chat...")
        client.monitor_chat("Siddharth Singh")
        
        print("Waiting for thread to start and hit an error...")
        time.sleep(15) # Give it 15 seconds to open the browser
        
        if client.monitor_thread and client.monitor_thread.is_alive():
            print("Thread is STILL ALIVE. Closing gracefully.")
            client.stop()
        else:
            print("THREAD DIED SILENTLY.")
    except Exception as e:
        print(f"MAIN THREAD ERROR:")
        traceback.print_exc()

if __name__ == "__main__":
    test()
