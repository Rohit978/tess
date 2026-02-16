import os
import json
from tess_cli.core.sandbox import Sandbox

class MockBrain:
    def think(self, prompt):
        if "risks" in prompt:
            return '{"rating": "SAFE", "reason": "Test command."}'
        return "This is a mock explanation of the simulation."

def test_sandbox():
    brain = MockBrain()
    sb = Sandbox(brain)
    
    print("--- TESS SANDBOX V2 VERIFICATION ---")
    
    # 1. Test Docker (if available)
    if sb.docker_client:
        print("\n[TEST 1] Testing Docker Isolation (Elite Tier)...")
        res = sb.simulate_command("echo 'Hello from Docker'")
        print(f"Engine: {res['engine']}")
        print(f"Output: {res['output']}")
        print(f"Interpretation: {res['prediction']}")
    else:
        print("\n[TEST 1] Skipping Docker (Module not active).")

    # 2. Test Restricted Subprocess (Universal Tier)
    print("\n[TEST 2] Testing Restricted Subprocess (Universal Tier)...")
    # Force subprocess by using a powershell-like command or just assuming Docker might skip it 
    # (actually we'll just check if it works)
    res = sb.simulate_command("whoami")
    print(f"Engine: {res['engine']}")
    print(f"Output: {res['output']}")
    print(f"Interpretation: {res['prediction']}")
    
    # 3. Test Safety Analysis
    print("\n[TEST 3] Testing Safety Analysis...")
    res = sb.simulate_command("rm -rf /")
    print(f"Safety Rating: {res['safety_rating']}")
    print(f"Safety Reason: {res['safety_reason']}")

    print("\nSandbox v2 Verification Complete!")

if __name__ == "__main__":
    test_sandbox()
