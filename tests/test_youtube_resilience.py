
import sys
import os
import time

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tess_cli.core.youtube_client import YouTubeClient, C

def test_resilience():
    print(f"{C.CYAN}🧪 Testing YouTube Client Resilience...{C.R}")
    
    # 1. Initialize
    client = YouTubeClient(headless=False)
    
    try:
        # 2. Start Session
        print(f"{C.DIM}Attempting to start session...{C.R}")
        client.start_session()
        
        # 3. Verify
        if client.is_page_active():
            print(f"{C.GREEN}✅ Session active!{C.R}")
            
            # Check if it fell back?
            # If client.browser is set, it means we used launch(), not launch_persistent_context()
            # launch_persistent_context returns a context, not a browser object directly (it's weird in playwright sync)
            # Actually, my code sets self.browser = browser in fallback.
            
            if client.browser:
                print(f"{C.YELLOW}⚠️ Using Temporary Profile (Fallback Active).{C.R}")
            else:
                print(f"{C.GREEN}✨ Using Persistent Profile.{C.R}")
                
            # 4. Search & Play (Quick check)
            print(f"{C.DIM}Testing play_video...{C.R}")
            result = client.play_video("Rick Roll")
            print(f"Result: {result}")
            
            time.sleep(5)
            client.stop()
            print(f"{C.GREEN}✅ Test Passed.{C.R}")
        else:
            print(f"{C.RED}❌ Session failed to start.{C.R}")
            
    except Exception as e:
        print(f"{C.RED}❌ Test Failed with Exception: {e}{C.R}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_resilience()
