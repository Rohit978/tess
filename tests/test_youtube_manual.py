
import sys
import os
import time

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tess_cli.core.youtube_client import YouTubeClient

def test_youtube():
    print("Testing YouTubeClient...")
    yt = YouTubeClient(headless=False)
    
    try:
        print("Starting session...")
        yt.start_session()
        
        query = "lofi hip hop radio"
        print(f"Playing video for query: {query}")
        result = yt.play_video(query)
        print(f"Result: {result}")
        
        if "Playing:" in result:
            print("SUCCESS: Video playback initiated.")
        else:
            print("FAILURE: Video playback failed.")
            
        # Keep it open for a bit
        time.sleep(10)
        
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("Stopping session...")
        yt.stop()

if __name__ == "__main__":
    test_youtube()
