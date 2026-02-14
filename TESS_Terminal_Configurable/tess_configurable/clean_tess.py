import os
import shutil
from pathlib import Path
import sys

def clean():
    root = Path(os.getcwd())
    print(f"Cleaning pycache in {root}...")
    
    count = 0
    for p in root.rglob("__pycache__"):
        try:
            print(f"Removing {p}")
            shutil.rmtree(p)
            count += 1
        except Exception as e:
            print(f"Failed to remove {p}: {e}")

    print(f"Done. Removed {count} cache directories.")
    print("Please now run: python -m tess_configurable.main")

if __name__ == "__main__":
    clean()
