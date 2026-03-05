
import sys
import os
import time
import requests
import threading

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tess_cli.skills.screencast import ScreencastSkill
from tess_cli.core.skill_loader import SkillLoader

def test_screencast_v2():
    print("🧪 Testing Screencast V2 Skill...")
    
    skill = ScreencastSkill(port=8080)
    
    print("  1. Starting Server...")
    res = skill.start()
    print(f"     Result: {res}")
    
    if "Screencast V2 Started" in res:
        print("  ✅ Server started successfully.")
    else:
        print(f"  ❌ Failed to start server: {res}")
        return

    # Give it a moment to bind
    time.sleep(2)

    try:
        print(f"  2. Checking URL http://127.0.0.1:{skill.port} ...")
        resp = requests.get(f"http://127.0.0.1:{skill.port}")
        
        if resp.status_code == 200:
             print("  ✅ UI loaded (HTTP 200).")
             if "TESS Remote V2" in resp.text:
                 print("  ✅ Correct V2 UI served.")
             else:
                 print("  ❌ Served content doesn't match V2 UI.")
        else:
             print(f"  ❌ HTTP Error: {resp.status_code}")

    except Exception as e:
        print(f"  ❌ Connection failed: {e}")

    print("  3. Stopping Server...")
    skill.stop()
    print("  ✅ Stopped.")

if __name__ == "__main__":
    test_screencast_v2()
