
import psutil
import socket
import os

print("--- Network Interfaces ---")
addrs = psutil.net_if_addrs()
for name, snics in addrs.items():
    for snic in snics:
        if snic.family == socket.AF_INET:
            print(f"Interface: {name}")
            print(f"  IP: {snic.address}")
            print(f"  Netmask: {snic.netmask}")
            print("-" * 20)

print("\n--- Testing Connectivity ---")
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    print(f"Default Gateway Route prefers IP: {s.getsockname()[0]}")
    s.close()
except Exception as e:
    print(f"Could not check default route: {e}")

print("\n--- Firewall Check (Basic) ---")
print("Note: If you cannot connect, Windows Firewall is the #1 cause.")
print("Try running this in Admin Terminal:")
print("netsh advfirewall firewall add rule name=\"TESS_Screencast\" dir=in action=allow protocol=TCP localport=8000-8010")
