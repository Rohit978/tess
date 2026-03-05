import time
import random
from tess_cli.core.face_client import FaceClient

client = FaceClient()

moods = ["IDLE", "THINKING", "BUSY", "SUCCESS", "ERROR"]

print("Testing TESS Face Expressions...")
try:
    while True:
        mood = random.choice(moods)
        print(f"Set Mood: {mood}")
        client.set_mood(mood)
        time.sleep(2)
except KeyboardInterrupt:
    print("Exiting...")
    client.close()
