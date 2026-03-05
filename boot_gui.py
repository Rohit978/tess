import subprocess
import sys
import os

def launch_gui():
    """Launch the TESS GUI (Dynamic Island) in a separate process."""
    if sys.platform == "win32":
        # Use pythonw to suppress console window for the GUI
        cmd = [sys.executable.replace("python.exe", "pythonw.exe"), "-m", "tess_cli.face.main_island"]
    else:
        cmd = [sys.executable, "-m", "tess_cli.face.main_island"]
        
    print("🚀 Launching TESS Dynamic Island...")
    subprocess.Popen(cmd, cwd=os.getcwd(), close_fds=True)

if __name__ == "__main__":
    launch_gui()
