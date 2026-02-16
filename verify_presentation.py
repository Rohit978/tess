import os
import sys
from tess_cli.skills.presentation_skill import PresentationSkill

class MockBrain:
    def think(self, prompt):
        return json.dumps([
            {"title": "Introduction", "bullets": ["First point", "Second point"]},
            {"title": "Middle", "bullets": ["A detail", "Another detail"]},
            {"title": "Conclusion", "bullets": ["Final thought"]}
        ])

import json

def verify_presentation():
    brain = MockBrain()
    skill = PresentationSkill(brain)
    
    print("--- TESS PRESENTATION VERIFICATION ---")
    
    # 1. Test PPTX Generation
    print("\n[TEST 1] Testing PPTX Generation (Style: Tech)...")
    res_pptx = skill.run("create", "AI Future", count=3, style="tech", format="pptx", output_name="test_ai_future")
    print(res_pptx)
    if os.path.exists("test_ai_future.pptx"):
        print("✅ PPTX created successfully.")
    else:
        print("❌ PPTX creation failed.")

    # 2. Test Marp Generation
    print("\n[TEST 2] Testing Marp Generation (Style: Uncover)...")
    res_md = skill.run("create", "Marp Test", count=3, style="uncover", format="md", output_name="test_marp")
    print(res_md)
    if os.path.exists("test_marp.md"):
        print("✅ Marp file created successfully.")
        with open("test_marp.md", "r") as f:
            content = f.read()
            if "theme: uncover" in content:
                print("✅ Marp theme correctly applied.")
            else:
                print("❌ Marp theme missing.")
    else:
        print("❌ Marp file creation failed.")

    print("\nVerification Complete!")

if __name__ == "__main__":
    verify_presentation()
