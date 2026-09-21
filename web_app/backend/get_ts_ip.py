import paramiko
import sys

ip = "165.101.47.50"
username = "root"
password = "Finn@03122001"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    ssh.connect(ip, username=username, password=password, timeout=10)
    stdin, stdout, stderr = ssh.exec_command("tailscale ip -4")
    ts_ip = stdout.read().decode('utf-8').strip()
    print(f"TAILSCALE_IP:{ts_ip}")
    ssh.close()
except Exception as e:
    print(f"Failed: {e}")
