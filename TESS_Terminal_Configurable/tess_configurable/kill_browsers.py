import os
import subprocess
import platform

def kill_browsers():
    print("Killing browser processes...")
    if platform.system() == "Windows":
        subprocess.run(["taskkill", "/F", "/IM", "chrome.exe"], capture_output=False)
        subprocess.run(["taskkill", "/F", "/IM", "msedge.exe"], capture_output=False)
        subprocess.run(["taskkill", "/F", "/IM", "node.exe"], capture_output=False)
    else:
        os.system("pkill -9 chrome")
        os.system("pkill -9 chromium")

    print("Browsers killed.")

if __name__ == "__main__":
    kill_browsers()
