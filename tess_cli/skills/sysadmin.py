
import subprocess
import platform
import logging

logger = logging.getLogger("SysAdminSkill")

class SysAdminSkill:
    """
    Advanced System Administration Skill using PowerShell.
    """
    
    def __init__(self):
        self.os_type = platform.system()
    
    def run(self, sub_action, **kwargs):
        if self.os_type != "Windows":
            return "Error: SysAdmin skill only supports Windows currently."
            
        try:
            if sub_action == "wifi_on":
                return self._set_wifi(True)
            elif sub_action == "wifi_off":
                return self._set_wifi(False)
            elif sub_action == "bluetooth_on":
                return self._set_bluetooth(True)
            elif sub_action == "bluetooth_off":
                return self._set_bluetooth(False)
            elif sub_action == "battery_status":
                return self._get_battery()
            elif sub_action == "system_info":
                return self._get_sys_info()
            elif sub_action == "mute_mic":
                return self._mute_mic(True)
            elif sub_action == "unmute_mic":
                return self._mute_mic(False)
            else:
                return f"Unknown SysAdmin action: {sub_action}"
        except Exception as e:
            logger.error(f"SysAdmin Error: {e}")
            return f"SysAdmin Failed: {e}"

    def _run_ps(self, script):
        cmd = ["powershell", "-NoProfile", "-Command", script]
        res = subprocess.run(cmd, capture_output=True, text=True)
        return res.stdout.strip() or res.stderr.strip()

    def _set_wifi(self, enable):
        state = "enable" if enable else "disable"
        # Requires Admin usually. TESS Executor runs as user, might fail if not elevated.
        # But 'netsh' sometimes works for user if interface is user-accessible?
        # Better: use 'netsh interface set interface "Wi-Fi" admin=...'
        script = f'netsh interface set interface "Wi-Fi" admin={state}'
        out = self._run_ps(script)
        return f"WiFi {state}d. Output: {out}"

    def _set_bluetooth(self, enable):
        # Bluetooth is tricky via pure CLI without heavy deps. 
        # Using a simple registry tweak or service toggle?
        # Service: bthserv
        action = "Start-Service" if enable else "Stop-Service"
        script = f"{action} bthserv"
        out = self._run_ps(script)
        return f"Bluetooth service {action}d. Output: {out}"

    def _get_battery(self):
        script = "Get-WmiObject Win32_Battery | Select-Object EstimatedChargeRemaining, BatteryStatus"
        out = self._run_ps(script)
        return f"Battery Status:\n{out}"

    def _get_sys_info(self):
        script = "systeminfo | Select-String 'OS Name','System Manufacturer','System Model','Total Physical Memory'"
        out = self._run_ps(script)
        return f"System Info:\n{out}"
    
    def _mute_mic(self, mute):
        # Requires nircmd or complex Audio API. 
        # PowerShell alone is hard for mic mute.
        # Placeholder
        return "Microphone control requires 'nircmd' or additional libraries. Not implemented yet."
