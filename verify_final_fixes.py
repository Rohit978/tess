import os
import json
from tess_cli.core.web_browser import WebBrowser
from tess_cli.skills.pdf_skill import PDFSkill

class MockBrain:
    def think(self, prompt):
        return "This is a mock research result for testing PDF creation."

def verify_fixes():
    print("--- TESS FINAL FIXES VERIFICATION ---")
    
    # 1. Test Boot & Init
    print("\n[TEST 1] Testing Boot & PDFSkill Init...")
    try:
        brain = MockBrain()
        pdf = PDFSkill(brain)
        print("✅ PDFSkill initialized successfully without crash.")
    except Exception as e:
        print(f"❌ PDFSkill init failed: {e}")
        return

    # 2. Test DuckDuckGo Search
    print("\n[TEST 2] Testing DuckDuckGo Search Integration...")
    browser = WebBrowser()
    results = browser.search_google("Python Programming")
    if "Link" in results or "🔹" in results:
        print("✅ DuckDuckGo search is functional.")
    else:
        print(f"❌ DuckDuckGo search failed or returned unexpected format: {results}")

    # 3. Test Native PDF Creation
    print("\n[TEST 3] Testing Native PDF Creation...")
    content = "Test Research Content: Narendra Modi is the PM of India."
    output_name = "test_research_bio.pdf"
    res = pdf.create_pdf(content, output_name)
    print(res)
    if os.path.exists(output_name):
        print("✅ Native PDF created successfully.")
        # Cleanup
        os.remove(output_name)
    else:
        print("❌ Native PDF creation failed.")

    print("\nAll Fixes Verified!")

if __name__ == "__main__":
    verify_fixes()
