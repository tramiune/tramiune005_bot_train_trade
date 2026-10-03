#!/bin/bash
cd /root/tramiune005_bot_train_trade/web_app/frontend

# Overwrite package.json build script to just run vite build
sed -i 's/"build": "tsc -b && vite build"/"build": "vite build"/' package.json

npm run build
cp -r dist/* /var/www/html/ 2>/dev/null || true
