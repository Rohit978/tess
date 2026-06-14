import subprocess
import os
import sys

class Executor:
    """Shell command execution with safety rails."""
    def __init__(self, safe_mode=True):
        self.safe_mode = safe_mode

    def execute_command(self, command):
        if not command: return "ERROR: Empty command."

        print(f"\n[TESS] > {command}")

        if self.safe_mode:
            if sys.stdin.isatty():
                confirm = input("Run? (Y/n): ").strip().lower()
                if confirm not in ['y', 'yes', 'ok', '']:
                    return "Cancelled."
            else:
                # Non-interactive: auto-approve in safe mode
                pass

        try:
            # Always route through PowerShell as an argv list (shell=False).
            # This prevents semicolon/pipe injection from LLM-generated strings.
            # -EncodedCommand is NOT used here to keep output readable.
            full_cmd = [
                "powershell", "-NoProfile", "-NonInteractive",
                "-ExecutionPolicy", "Bypass",
                "-Command", command
            ]

            res = subprocess.run(
                full_cmd,
                shell=False,        # Never shell=True — prevents injection
                capture_output=True,
                text=True,
                cwd=os.getcwd(),
                timeout=60
            )

            return res.stdout + (f"\n[STDERR]: {res.stderr}" if res.stderr else "")

        except subprocess.TimeoutExpired:
            return "Exec Failed: Command timed out after 60 seconds."
        except Exception as e:
            return f"Exec Failed: {e}"
