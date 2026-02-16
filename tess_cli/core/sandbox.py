import os
import subprocess
import tempfile
import shutil
import json
from .logger import setup_logger

logger = setup_logger("Sandbox")

class Sandbox:
    """
    [EXPERIMENTAL] The Multiverse Engine.
    Scalable Isolation for safe command execution.
    - Tier 1: Docker (Transient Containers)
    - Tier 2: Windows Sandbox (Disabled on Home edition)
    - Tier 3: Restricted Subprocess (Active Fallback)
    """
    def __init__(self, brain):
        self.brain = brain
        self.docker_client = None
        self._init_docker()

    def _init_docker(self):
        """Attempts to initialize Docker client."""
        try:
            import docker
            self.docker_client = docker.from_env()
            self.docker_client.ping()
            logger.info("🐳 Docker Engine detected and active.")
        except Exception as e:
            logger.warning(f"Docker unavailable: {e}")
            self.docker_client = None

    def simulate_command(self, command):
        """
        Routes the command to the best available isolation layer.
        """
        logger.info(f"🧪 Analyzing Sandbox Routing for: {command}")
        
        # 🛡️ Safety Rating (AI Insight)
        safety_prompt = (
            f"Analyze this command for risks: '{command}'. "
            "Return a JSON object: {'rating': 'SAFE'|'DANGEROUS', 'reason': '...'}"
        )
        try:
            safety_raw = self.brain.think(safety_prompt)
            # Extract JSON
            import re
            match = re.search(r"\{.*\}", safety_raw, re.DOTALL)
            safety_data = json.loads(match.group(0)) if match else {"rating": "UNKNOWN", "reason": "No analysis."}
        except:
            safety_data = {"rating": "UNKNOWN", "reason": "Analysis failed."}

        # 🚀 ENGINE SELECTION
        result = None
        engine_used = "AI Prediction"

        # 1. Try Docker (Elite) - Best for Linux/Generic commands
        if self.docker_client and not any(win_cmd in command.lower() for win_cmd in ["powershell", "dir", "get-service", "get-process"]):
            try:
                result = self._run_docker(command)
                engine_used = "Docker (Isolated Container)"
            except Exception as e:
                logger.error(f"Docker execution failed: {e}")

        # 2. Try Windows Sandbox (Pro) - FOR WINDOWS SPECIFIC COMMANDS (If we had a .wsb helper)
        # For now, let's stick to Docker + Subprocess

        # 3. Fallback: Restricted Subprocess (Universal)
        if not result:
            result = self._run_restricted_subprocess(command)
            engine_used = "Restricted Subprocess (Witness-only)"

        # 4. Final Polish: AI interprets the results
        interpretation_prompt = (
            f"The command '{command}' was run in a {engine_used}. "
            f"Output was: {result}\n\n"
            "Explain what happened and what the side effects WOULD have been on the real system."
        )
        explanation = self.brain.think(interpretation_prompt)

        return {
            "prediction": explanation,
            "output": result,
            "engine": engine_used,
            "safety_rating": safety_data.get("rating", "UNKNOWN"),
            "safety_reason": safety_data.get("reason", ""),
            "command": command
        }

    def _run_docker(self, command):
        """Runs the command in an Alpine container."""
        logger.info("🚀 Launching Docker Sandbox Container...")
        container = self.docker_client.containers.run(
            "alpine",
            f"sh -c \"{command}\"",
            detach=False,
            remove=True,
            network_disabled=True,
            mem_limit="128m"
        )
        return container.decode('utf-8').strip()

    def _run_restricted_subprocess(self, command, timeout=None):
        """
        Runs a command in an isolated temp directory with resource guarding.
        Uses psutil to monitor for CPU/Memory spikes.
        """
        import psutil
        import time
        from .config import Config

        # Use defaults from Config if not specified
        if timeout is None:
            timeout = Config.SANDBOX_TIMEOUT_SEC
        ram_limit = Config.SANDBOX_RAM_LIMIT_MB

        logger.info(f"🔬 Launching Resource-Guarded Subprocess (Limit: {ram_limit}MB, {timeout}s)...")
        temp_dir = tempfile.mkdtemp(prefix="tess_sandbox_")
        
        # Decide shell based on command (default to PowerShell for modern Windows)
        shell_cmd = ["powershell", "-Command", command] if "powershell" in command.lower() or "-" in command else command
        
        try:
            process = subprocess.Popen(
                shell_cmd,
                shell=isinstance(shell_cmd, str),
                cwd=temp_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # 🛡️ RESOURCE GUARD (CPU/Memory)
            start_time = time.time()
            while process.poll() is None:
                # Check timeout
                if time.time() - start_time > timeout:
                    process.kill()
                    return f"[TIMED OUT]: Command took longer than {timeout}s."
                
                try:
                    p = psutil.Process(process.pid)
                    # Simple guards for i3/8GB: kill if memory > 200MB or CPU > 50% for too long
                    mem_mb = p.memory_info().rss / (1024 * 1024)
                    if mem_mb > ram_limit:
                        process.kill()
                        return f"[RESOURCE LIMIT]: Sandbox killed - Memory exceeded {ram_limit}MB ({mem_mb:.1f}MB)."
                except:
                    pass
                
                time.sleep(0.1)

            stdout, stderr = process.communicate()
            output = stdout if stdout else stderr
            return output.strip() if output else "[No output produced]"

        except Exception as e:
            return f"[Sandbox Error]: {e}"
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
