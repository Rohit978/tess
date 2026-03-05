
import sys
import os
import time

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tess_cli.skills.screencast import ScreencastSkill

def test_screencast():
    print("Initializing ScreencastSkill...")
    skill = ScreencastSkill(port=8000)
    
    print("Attempting to start broadcast...")
    result = skill.start()
    print(f"Start Result: {result}")
    
    if "Rocket" in result or "started" in result:
        print("SUCCESS: Broadcast started successfully.")
        print(f"IP: {skill.get_ip()}")
        print(f"Port: {skill.port}")
    else:
        print("FAILURE: Broadcast failed to start.")
        
    # Keep it running for a few seconds to verify stability (optional)
    time.sleep(2)
    
    print("Stopping broadcast...")
    stop_result = skill.stop()
    print(f"Stop Result: {stop_result}")

if __name__ == "__main__":
    test_screencast()
