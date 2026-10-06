ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp
ufw allow in on tailscale0 to any port 80
ufw allow in on tailscale0 to any port 81
ufw allow in on tailscale0 to any port 82
ufw allow in on tailscale0 to any port 8000
ufw allow in on tailscale0 to any port 8001
ufw --force enable
