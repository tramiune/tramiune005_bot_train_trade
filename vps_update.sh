cd /root/bot_xrp && git pull origin main
cd /root/bot_sol && git pull origin main
pm2 restart bot-xrp
pm2 restart bot-sol
pm2 status
