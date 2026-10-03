#!/bin/bash
set -e

echo "=== System Update & Install Dependencies ==="
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y git python3-venv python3-pip curl nginx ufw sqlite3
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt-get install -y nodejs
npm install -g pm2

echo "=== Clone Repository ==="
cd /root
if [ -d "tramiune005_bot_train_trade" ]; then
    cd tramiune005_bot_train_trade
    git pull
else
    git clone https://github.com/tramiune/tramiune005_bot_train_trade.git
    cd tramiune005_bot_train_trade
fi

echo "=== Setup Backend ==="
cd /root/tramiune005_bot_train_trade/web_app/backend
cp /root/.env.backup .env
cp /root/trading_bot.db.backup trading_bot.db
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install uvicorn gunicorn

echo "=== Setup Frontend ==="
cd /root/tramiune005_bot_train_trade/web_app/frontend
npm install
npm run build

echo "=== Configure Nginx ==="
cat << 'NGINX' > /etc/nginx/sites-available/default
server {
    listen 80 default_server;
    listen [::]:80 default_server;

    root /root/tramiune005_bot_train_trade/web_app/frontend/dist;
    index index.html index.htm;
    
    server_name _;

    location / {
        try_files $uri $uri/ /index.html;
    }
}
NGINX
# Nginx needs access to /root
usermod -aG root www-data
chmod 755 /root
chmod -R 755 /root/tramiune005_bot_train_trade/web_app/frontend/dist

systemctl restart nginx

echo "=== Configure Firewall ==="
ufw allow 'Nginx Full'
ufw allow 8000
ufw allow ssh
ufw --force enable

echo "=== Start Backend with PM2 ==="
cd /root/tramiune005_bot_train_trade/web_app/backend
pm2 delete backend || true
pm2 start "source .venv/bin/activate && uvicorn main:app --host 0.0.0.0 --port 8000" --name backend
pm2 save
pm2 startup | tail -n 1 > /tmp/pm2_startup.sh
bash /tmp/pm2_startup.sh

echo "=== Deployment Completed! ==="
