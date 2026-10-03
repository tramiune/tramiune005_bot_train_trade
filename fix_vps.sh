#!/bin/bash
set -e

cd /root/tramiune005_bot_train_trade
git fetch origin
git reset --hard origin/main
git checkout main
git pull origin main

cd /root/tramiune005_bot_train_trade/web_app/backend
pm2 stop backend || true
pm2 delete backend || true
pm2 start ./start.sh --name backend
pm2 save

cd /root/tramiune005_bot_train_trade/web_app/frontend
npm run build
cp -r dist/* /var/www/html/ 2>/dev/null || true

systemctl restart nginx
