import subprocess
import json
import os
import difflib

class AppLauncher:
    """
    Manages installed application discovery and launching.
    Uses 'Get-StartApps' to find AppUserModelIDs.
    """
    
    def __init__(self, data_file="known_apps.json"):
        self.data_file = os.path.join(os.path.dirname(__file__), data_file)
        self.apps = self.load_apps()

    def load_apps(self):
        """Load known apps from JSON file."""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    return json.load(f)
            except:
                return []
        return []

    def scan_apps(self):
        """
        Scans for all installed apps using PowerShell Get-StartApps.
        """
        print("Scanning installed applications... (this may take a moment)")
        # Get-StartApps | ConvertTo-Json
        # Note: We need to handle encoding properly
        command = "Get-StartApps | Select-Object Name, AppID | ConvertTo-Json -Depth 1"
        
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", command],
                capture_output=True,
                text=True,
                encoding='utf-8' # or cp1252 depending on system
            )
            
            if result.returncode != 0:
                return f"Error scanning apps: {result.stderr}"
            
            # Parse JSON output
            try:
                apps_data = json.loads(result.stdout)
                # Parse output - it might be a single dict or list of dicts
                if isinstance(apps_data, dict):
                    apps_data = [apps_data]
                    
                self.apps = apps_data
                
                # Save to file
                with open(self.data_file, 'w') as f:
                    json.dump(self.apps, f, indent=2)
                    
                return f"Successfully scanned {len(self.apps)} apps."
                
            except json.JSONDecodeError:
                return "Error parsing Get-StartApps output. Raw output might be invalid JSON."
                
        except Exception as e:
            return f"Scan failed: {str(e)}"

    def launch_app(self, app_name):
        """
        Discovery and Execution combo.
        """
        cmd = self.get_launch_command(app_name)
        if not cmd:
            return f"Error: Could not find application '{app_name}'"
            
        try:
            subprocess.run(["powershell", "-NoProfile", "-Command", cmd], check=True)
            return f"Launched {app_name}"
        except Exception as e:
            return f"Failed to launch {app_name}: {e}"

    def find_app(self, app_name):
        """
        Fuzzy search for an app by name.
        """
        if not app_name or not self.apps:
            return None
            
        app_name_lower = str(app_name).lower()
            
        # 1. Exact case-insensitive match
        for app in self.apps:
            name = app.get('Name')
            if name and name.lower() == app_name_lower:
                return app
                
        # 2. Contains match
        matches = []
        for app in self.apps:
            name = app.get('Name')
            if name and app_name_lower in name.lower():
                matches.append(app)
                
        if matches:
            # Return shortest match (likely the most exact one)
            matches.sort(key=lambda x: len(x.get('Name', '')))
            return matches[0]
            
        # 3. Difflib close match (optional, can be skipped for speed)
        return None

    def get_launch_command(self, app_name):
        """
        Returns the PowerShell command to launch the app.
        """
        app = self.find_app(app_name)
        if app:
            return f"Start-Process shell:AppsFolder\\{app['AppID']}"
            
        # Fallback: Try running as a direct command (for things like 'notepad', 'calc', 'msedge')
        # Only allow explicitly known common executables to prevent PowerShell hangs
        common_exes = ["notepad", "calc", "msedge", "chrome", "firefox", "explorer", "cmd", "powershell", "code"]
        if app_name.lower() in common_exes:
             return f"Start-Process {app_name}"
             
        return None
