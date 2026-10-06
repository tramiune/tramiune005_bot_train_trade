pm2 delete bot-xrp || true
cd /root/bot_xrp/web_app/backend
pm2 start "source .venv/bin/activate && uvicorn main:app --host 0.0.0.0 --port 8000" --name bot-xrp

pm2 delete bot-sol || true
cd /root/bot_sol/web_app/backend
pm2 start "source .venv/bin/activate && uvicorn main:app --host 0.0.0.0 --port 8001" --name bot-sol
pm2 save

cat << 'NGINX' > /etc/nginx/sites-available/default
server {
    listen 80 default_server;
    root /root/bot_xrp/web_app/frontend/dist;
    index index.html index.htm;
    server_name _;
    location / { try_files \$uri \$uri/ /index.html; }
    location /api/ { proxy_pass http://127.0.0.1:8000/api/; }
}
server {
    listen 81;
    root /root/bot_sol/web_app/frontend/dist;
    index index.html index.htm;
    server_name _;
    location / { try_files \$uri \$uri/ /index.html; }
    location /api/ { proxy_pass http://127.0.0.1:8001/api/; }
}
NGINX

ufw allow 81 || true
systemctl restart nginx
