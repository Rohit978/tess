
import sys
import os
import psutil
import socket

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tess_cli.skills.screencast import ScreencastSkill

def test_ip():
    print("🧪 Testing IP Detection...")
    
    # 1. Print all available IPs for debugging
    print("  Available IPs:")
    for interface, snics in psutil.net_if_addrs().items():
        for snic in snics:
            if snic.family == socket.AF_INET:
                print(f"    - {interface}: {snic.address}")

    # 2. Test get_ip()
    skill = ScreencastSkill()
    detected_ip = skill.get_ip()
    print(f"\n  ✅ Detected IP: {detected_ip}")
    
    if detected_ip.startswith("10.") or detected_ip.startswith("192.168."):
        print("  🎉 Success: Picked a LAN IP.")
    else:
        print("  ⚠️ Check if this is the desired IP.")

if __name__ == "__main__":
    test_ip()
