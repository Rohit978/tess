"""
Standalone test for ScreencastSkill.
Run from the project root:  python test_screencast.py
"""
import sys
import time
import webbrowser

# Make sure tess_cli is importable from the project root
sys.path.insert(0, ".")

from tess_cli.skills.screencast import ScreencastSkill

skill = ScreencastSkill(brain=None, port=8000)

print("Starting screencast server…")
result = skill.start()
print(result)

# Extract URL and open browser
url = None
for word in result.split():
    if word.startswith("http://"):
        url = word
        break

if url:
    print(f"\nOpening {url} in browser…")
    webbrowser.open(url)
else:
    print("Could not detect server URL.")

print("\nPress Ctrl+C to stop.\n")
try:
    while True:
        status = skill.status()
        print(f"\r{status}", end="", flush=True)
        time.sleep(2)
except KeyboardInterrupt:
    print("\n\nStopping…")
    print(skill.stop())
