import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from tess_cli.core.youtube_client import YouTubeClient

print("Starting YouTubeClient test in HEADED mode...")
try:
    yt = YouTubeClient(headless=False)
    print("Client initialized. Trying to play video...")
    result = yt.play_video("they call this love")
    print(f"Result: {result}")
except Exception as e:
    print(f"Exception: {e}")
