#!/bin/bash
cd /root/tramiune005_bot_train_trade
git pull origin main

cd web_app/frontend
npm run build
cp -r dist/* /var/www/html/ 2>/dev/null || true
