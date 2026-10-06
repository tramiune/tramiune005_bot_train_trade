cd /root/bot_xrp && git pull origin main
cd /root/bot_sol && git pull origin main

# Add cron job: runs at 08:00 and 20:00 every day
(crontab -l 2>/dev/null | grep -v "health_monitor.py" ; echo "0 8,20 * * * PYTHONPATH=/root/bot_xrp/web_app/backend /root/bot_xrp/web_app/backend/.venv/bin/python /root/bot_xrp/web_app/backend/health_monitor.py > /var/log/health_monitor.log 2>&1") | crontab -

echo "Current crontab:"
crontab -l

# Test run now
PYTHONPATH=/root/bot_xrp/web_app/backend /root/bot_xrp/web_app/backend/.venv/bin/python /root/bot_xrp/web_app/backend/health_monitor.py
