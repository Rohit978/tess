import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from tess_cli.core.config import Config
from tess_cli.core.brain import Brain

print(f"Current Config Personality: {Config._data['advanced'].get('personality', 'casual')}")
brain = Brain()
print("Asking TESS a simple question in Rogue Mode...")
response = brain.generate_command("Can you explain what a Python dictionary is?")
print(f"\nTESS Response:\n{response}")
