
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tess_cli.core.user_profile import UserProfile
from tess_cli.core.web_browser import WebBrowser

def test_personality_setter():
    print("Testing UserProfile.personality setter...")
    try:
        profile = UserProfile()
        print(f"Current personality: {profile.personality}")
        profile.personality = "cute"
        print(f"New personality: {profile.personality}")
        
        if profile.personality == "cute":
            print("✅ SUCCESS: Personality setter works.")
        else:
            print("❌ FAIL: Personality did not update.")
            
    except AttributeError as e:
        print(f"❌ FAIL: AttributeError - {e}")
    except Exception as e:
        print(f"❌ FAIL: {e}")

def test_search():
    print("\nTesting WebBrowser.search_google...")
    try:
        wb = WebBrowser()
        res = wb.search_google("test execution", headless=True)
        print(f"Search Result Length: {len(res)}")
        if "No results" in res or "timeout" in res:
             print(f"⚠️ WARNING: Search might be flaky. Result: {res[:100]}")
        else:
             print("✅ SUCCESS: Search returned results.")
    except Exception as e:
        print(f"❌ FAIL: Search crashed - {e}")

if __name__ == "__main__":
    test_personality_setter()
    test_search()
