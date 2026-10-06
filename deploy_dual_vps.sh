#!/bin/bash
set -e

echo "=== Triển Khai Hệ Thống BOT Kép (XRP & SOL) ==="

# Kéo code mới nhất về
cd /root/tramiune005_bot_train_trade
git pull origin main

# Tách làm 2 thư mục riêng biệt cho 2 Bot
cd /root
cp -r tramiune005_bot_train_trade bot_xrp
cp -r tramiune005_bot_train_trade bot_sol

# Setup BOT XRP
echo "=== Setup BOT XRP (Cổng 8000) ==="
cd /root/bot_xrp/web_app/backend
# Thêm BOT_MODE vào .env
if ! grep -q "BOT_MODE" .env; then
    echo -e "\nBOT_MODE=XRP" >> .env
fi
sed -i 's/BOT_MODE=.*/BOT_MODE=XRP/g' .env
pm2 delete bot-xrp || true
pm2 start "source .venv/bin/activate && python ws_engine.py" --name bot-xrp

# Setup BOT SOL
echo "=== Setup BOT SOL (Cổng 8001) ==="
cd /root/bot_sol/web_app/backend
# Thêm BOT_MODE vào .env
if ! grep -q "BOT_MODE" .env; then
    echo -e "\nBOT_MODE=SOL" >> .env
fi
sed -i 's/BOT_MODE=.*/BOT_MODE=SOL/g' .env
pm2 delete bot-sol || true
pm2 start "source .venv/bin/activate && python ws_engine.py" --name bot-sol

pm2 save
echo "=== Hoàn Thành! 2 Bot Đã Chạy Độc Lập ==="
