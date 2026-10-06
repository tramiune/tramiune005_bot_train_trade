cd /root/bot_xrp && git pull origin main
cd /root/bot_sol && git pull origin main

# Install psutil if needed
/root/bot_xrp/web_app/backend/.venv/bin/pip install psutil

# Test run once to send live report
PYTHONPATH=/root/bot_xrp/web_app/backend /root/bot_xrp/web_app/backend/.venv/bin/python /root/bot_xrp/web_app/backend/health_monitor.py

# Check existing crontab
crontab -l > /tmp/mycron || true

# Remove old health_monitor entries if any
grep -v "health_monitor.py" /tmp/mycron > /tmp/mycron_new || true

# Add 08:00 and 20:00 VN time (01:00 and 13:00 UTC)
# In Linux VPS, let's check VPS timezone
echo "0 8,20 * * * /usr/bin/python3 -c ''" >> /dev/null
# Check timezone of VPS
