import paramiko
import sys
import time

ip = "165.101.47.50"
username = "root"
password = "Finn@03122001"

commands = [
    "apt-get update",
    "apt-get install -y python3 python3-pip python3-venv git curl",
    "curl -fsSL https://tailscale.com/install.sh | sh",
    "mkdir -p /opt/trading-bot",
    "tailscale status || echo 'Tailscale installed but not authenticated'"
]

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    ssh.connect(ip, username=username, password=password, timeout=10)
    for cmd in commands:
        print(f"\n--- Running: {cmd} ---")
        stdin, stdout, stderr = ssh.exec_command(cmd)
        
        # Stream output
        while True:
            line = stdout.readline()
            if not line:
                break
            print(line.strip())
            
        err = stderr.read().decode()
        if err:
            print(f"STDERR: {err}")
            
    ssh.close()
    sys.exit(0)
except Exception as e:
    print(f"Failed: {e}")
    sys.exit(1)
