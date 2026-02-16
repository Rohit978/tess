import sys
import os
import asyncio

# Add project root to path
sys.path.append(os.getcwd())

from tess_cli.core.web_browser import WebBrowser
from tess_cli.core.youtube_client import YouTubeClient

def test_search():
    print("Testing Search...")
    wb = WebBrowser()
    res = wb.search_google("Narendra Modi")
    print(f"Search Results Sample: {res[:500]}...")
    if "Link" in res or "🔹" in res:
        print("✅ Search test passed (API working)")
    else:
        print("❌ Search test failed or returned unexpected format")

def test_youtube_init():
    print("\nTesting YouTube Init (Headless)...")
    # Using headless=True for verification to avoid popping up a browser on the user's screen during test
    yt = YouTubeClient(headless=True)
    try:
        yt.start_session()
        print("✅ YouTube Session successfully initialized.")
        yt.stop()
    except Exception as e:
        print(f"❌ YouTube Session failed: {e}")

if __name__ == "__main__":
    test_search()
    # Note: test_youtube_init might fail in some environments without proper display/setup,
    # but we'll try it.
    test_youtube_init()
