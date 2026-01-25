import socket
import urllib.request
import json
import sys

def check_port(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def check_engine_health():
    try:
        with urllib.request.urlopen('http://localhost:3002/health', timeout=2) as r:
            if r.status == 200:
                data = json.loads(r.read().decode())
                return True, data
    except Exception as e:
        return False, str(e)
    return False, "Unknown error"

print("--- SENTIENT ALPHA HEALTH CHECK ---")
status_3000 = check_port(3000)
status_3002 = check_port(3002)

print(f"PORT 3000 (Frontend): {'[ONLINE]' if status_3000 else '[OFFLINE]'}")
print(f"PORT 3002 (Engine):   {'[ONLINE]' if status_3002 else '[OFFLINE]'}")

if status_3002:
    alive, info = check_engine_health()
    if alive:
        print(f"ENGINE STATUS: [HEALTHY] (Agents: {info.get('agents')}, Balance: ${info.get('balance')})")
    else:
        print(f"ENGINE STATUS: [UNRESPONSIVE] - Error: {info}")
        print("ADVICE: Port 3002 is active but not serving health checks. Check for process conflicts.")
else:
    print("ENGINE STATUS: [OFFLINE]")
    print("ADVICE: Run 'python3 engine/main.py' to start the backbone.")

print("-----------------------------------")
