import subprocess
import time
import sys
import os

# Production Grade features:
# 1. Immortality (Service Wrapper)
# 2. Logs
# 3. Clean environment

PROCESS_NAME = "TESS"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def start_tess():
    print(f"🚀 [SUPERVISOR] Starting {PROCESS_NAME}...")
    try:
        # Run FastAPI Server and wait for it
        # We use python -m uvicorn because it's installed in venv
        print(f"🌍 [SUPERVISOR] Launching Web Interface & Core from {SCRIPT_DIR}...")
        
        # Ensure SCRIPT_DIR is in PYTHONPATH
        env = os.environ.copy()
        env["PYTHONPATH"] = SCRIPT_DIR + os.pathsep + env.get("PYTHONPATH", "")
        
        result = subprocess.run(
            [sys.executable, "-m", "src.api.server"], 
            cwd=SCRIPT_DIR,
            env=env,
            check=False
        )
        return result.returncode
    except KeyboardInterrupt:
        print("\n🛑 [SUPERVISOR] Stopped by user.")
        return 0
    except Exception as e:
        print(f"⚠️ [SUPERVISOR] Crash detected: {e}")
        return 1

if __name__ == "__main__":
    print("--------------------------------------------------")
    print("       TESS SUPERVISOR (IMMORTALITY MODE)")
    print("--------------------------------------------------")
    print("This wrapper keeps TESS alive even if it crashes.")
    print("Press Ctrl+C to stop the Supervisor.")
    
    while True:
        code = start_tess()
        if code == 0:
            print("✅ [SUPERVISOR] TESS exited normally.")
            break
        else:
            print(f"⚠️ [SUPERVISOR] TESS exited with code {code}. Restarting in 3s...")
            time.sleep(3)
