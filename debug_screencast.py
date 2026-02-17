
import sys
import os
import traceback

print("DEBUG: Starting import check...")
try:
    import tess_cli
    print(f"DEBUG: tess_cli location: {tess_cli.__file__}")
except ImportError:
    print("DEBUG: Could not import tess_cli package")

try:
    print("DEBUG: Attempting to import pyautogui...")
    import pyautogui
    print(f"DEBUG: pyautogui imported successfully from {pyautogui.__file__}")
except Exception:
    print("DEBUG: Failed to import pyautogui")
    traceback.print_exc()

try:
    print("DEBUG: Attempting to import ScreencastSkill...")
    from tess_cli.skills.screencast import ScreencastSkill
    print("DEBUG: ScreencastSkill imported successfully!")
except Exception:
    print("DEBUG: Failed to import ScreencastSkill")
    traceback.print_exc()
