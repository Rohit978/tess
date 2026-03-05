
import sys
import os
import json

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tess_cli.core.brain import Brain

def test_json_parsing():
    video_brain = Brain() # Minimal init
    
    # Test Case 1: Extra Data
    malformed_1 = '{"action": "broadcast_op", "sub_action": "start"} I hope this works!'
    print(f"Testing: {malformed_1}")
    res_1 = video_brain._parse_json(malformed_1)
    print(f"Result: {res_1}")
    assert res_1.get("action") == "broadcast_op"
    
    # Test Case 2: Markdown Blocks
    malformed_2 = 'Here is the JSON:\n```json\n{"action": "youtube_op", "query": "lofi"}\n```\nEnjoy the music!'
    print(f"\nTesting: {malformed_2}")
    res_2 = video_brain._parse_json(malformed_2)
    print(f"Result: {res_2}")
    assert res_2.get("action") == "youtube_op"
    
    # Test Case 3: Multiple Objects (Should take first)
    malformed_3 = '{"action": "first"} {"action": "second"}'
    print(f"\nTesting: {malformed_3}")
    res_3 = video_brain._parse_json(malformed_3)
    print(f"Result: {res_3}")
    assert res_3.get("action") == "first"

    print("\n✅ All JSON parsing tests passed!")

if __name__ == "__main__":
    test_json_parsing()
