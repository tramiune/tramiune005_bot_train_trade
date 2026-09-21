import paramiko
import sys
import select

ip = "165.101.47.50"
username = "root"
password = "Finn@03122001"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    ssh.connect(ip, username=username, password=password, timeout=10)
    print("Running tailscale up...")
    stdin, stdout, stderr = ssh.exec_command("tailscale up", get_pty=True)
    
    # Wait for the login URL
    while True:
        if stdout.channel.recv_ready():
            output = stdout.channel.recv(1024).decode('utf-8')
            print(output, end='')
            if "https://login.tailscale.com" in output or "Success" in output:
                break
        if stdout.channel.exit_status_ready():
            break
            
    ssh.close()
except Exception as e:
    print(f"Failed: {e}")
