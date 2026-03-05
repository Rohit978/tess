import sys
import os
import logging

logging.basicConfig(level=logging.DEBUG)

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tess_cli.core.config import Config
from tess_cli.core.brain import Brain

brain = Brain()
print("Initialized Brain")

user_input = r'index file at "C:\Users\01roh\Downloads\Dharmansh Dixit.docx"'
print(f"Sending input to generate_command: {user_input}")

try:
    response = brain.generate_command(user_input)
    print("Response received:")
    print(response)
except Exception as e:
    print(f"Error: {e}")
