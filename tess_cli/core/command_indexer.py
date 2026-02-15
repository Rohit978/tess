import os
import json
import subprocess
import time
from .logger import setup_logger
from .knowledge_base import KnowledgeBase
from .config import Config

logger = setup_logger("CommandIndexer")

class CommandIndexer:
    """
    Scans system commands, fetches help text/docs, and indexes them into ChromaDB.
    """
    def __init__(self, knowledge_base: KnowledgeBase):
        self.kb = knowledge_base
        self.kb_collection = self.kb.collection # Direct access to chroma collection

    def index_system_commands(self):
        """
        Main entry point: Scans, enriches, and indexes commands.
        """
        logger.info("Starting System Command Indexing...")
        
        # 1. Run PowerShell Scanner
        commands = self._scan_commands_powershell()
        if not commands:
            logger.error("No commands found from PowerShell scan.")
            return "Scan failed."
            
        logger.info(f"Found {len(commands)} candidate commands. Processing...")
        
        count = 0
        for cmd_info in commands:
            name = cmd_info.get("Name")
            path = cmd_info.get("Source") or cmd_info.get("Path")
            cmd_type = cmd_info.get("Type", "Application")
            
            # 2. Enrich with Help Text + Docs
            help_text = self._get_command_help(name, cmd_type)
            doc_text = self._scan_local_docs(path)
            
            definition = f"Definition: {cmd_info.get('Definition')}\n" if cmd_info.get('Definition') else ""
            full_content = f"Command: {name}\nType: {cmd_type}\n{definition}Path: {path}\n\n[HELP OUTPUT]\n{help_text}\n\n[LOCAL DOCS]\n{doc_text}"
            
            # 3. Upsert to ChromaDB
            try:
                # We use specific IDs to allow updates
                doc_id = f"cmd_{name}"
                
                self.kb_collection.upsert(
                    documents=[full_content],
                    metadatas=[{"type": "command", "name": name, "type": cmd_type, "path": str(path)}],
                    ids=[doc_id]
                )
                logger.debug(f"Indexed {cmd_type}: {name}")
                count += 1
                
                # Report progress every 20 items
                if count % 20 == 0:
                    print(f"Indexed {count}/{len(commands)} commands...", end="\r")
                    
            except Exception as e:
                logger.error(f"Failed to index {name}: {e}")

        print(f"\nFinalized indexing of {count} commands.")
        return f"Successfully indexed {count} system commands."

    def _scan_commands_powershell(self):
        """Runs the PS1 script to get JSON list of commands."""
        # Fix: Use path relative to package installation, not CWD
        base_dir = os.path.dirname(os.path.dirname(__file__)) # tess_cli/
        script_path = os.path.join(base_dir, "scripts", "scan_commands.ps1")
        if not os.path.exists(script_path):
            logger.error(f"Script not found: {script_path}")
            return []
            
        try:
            cmd = ["powershell", "-ExecutionPolicy", "Bypass", "-File", script_path]
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
            
            # Find JSON in output (skip "Scanning..." text)
            output = result.stdout
            json_start = output.find("[")
            if json_start != -1:
                json_str = output[json_start:]
                return json.loads(json_str)
            return []
        except Exception as e:
            logger.error(f"PowerShell scan error: {e}")
            return []

    def _get_command_help(self, name, cmd_type="Application"):
        """Fetches usage info. Uses Get-Help for PS native, --help for external."""
        try:
            # For Cmdlets/Functions/Aliases, Get-Help is much better
            if cmd_type in ["Cmdlet", "Function", "Alias"]:
                cmd = ["powershell", "-NoProfile", "-Command", f"Get-Help {name} -Full | Out-String"]
            else:
                # External EXE fallback
                cmd = [name, "--help"]

            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                encoding='utf-8', 
                errors='ignore', 
                timeout=3
            )
            return result.stdout.strip()[:2000] # Limit to 2000 chars
        except subprocess.TimeoutExpired:
            return "Help command timed out."
        except FileNotFoundError:
            return "Command not found in PATH."
        except Exception:
            try:
                # Try /? for windows native
                result = subprocess.run(
                    [name, "/?"], 
                    capture_output=True, 
                    text=True, 
                    encoding='utf-8', 
                    errors='ignore', 
                    timeout=3
                )
                return result.stdout.strip()[:2000]
            except:
                return "No help output available."

    def _scan_local_docs(self, exe_path):
        """Looks for README.md or standard doc files near the executable."""
        if not exe_path or not os.path.exists(exe_path):
            return ""
            
        folder = os.path.dirname(exe_path)
        doc_content = ""
        
        # Common filenames
        targets = ["README.md", "README.txt", "MANUAL.txt", "LICENSE.txt"]
        
        for t in targets:
            p = os.path.join(folder, t)
            if os.path.exists(p):
                try:
                    with open(p, 'r', encoding='utf-8', errors='ignore') as f:
                        # Read first 1kb of docs
                        doc_content += f"\n--- {t} ---\n{f.read(1000)}...\n"
                except: pass
                
        return doc_content
