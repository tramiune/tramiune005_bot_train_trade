mkdir -p /var/www/master_ui
cat << 'HTML' > /var/www/master_ui/index.html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Quant Command Center</title>
    <style>
        body { margin: 0; padding: 0; font-family: sans-serif; background: #0B0E14; color: white; display: flex; flex-direction: column; height: 100vh; }
        .tabs { display: flex; background: #1E222D; border-bottom: 1px solid #333; }
        .tab { padding: 15px 30px; cursor: pointer; font-weight: bold; color: #888; border-bottom: 3px solid transparent; }
        .tab:hover { color: #fff; }
        .tab.active { color: #fff; border-bottom-color: #2563EB; }
        iframe { flex: 1; width: 100%; border: none; }
    </style>
</head>
<body>
    <div class="tabs">
        <div class="tab active" onclick="switchTab('xrp', this)">XRP BOT (5m)</div>
        <div class="tab" onclick="switchTab('sol', this)">SOL BOT (4H)</div>
    </div>
    <iframe id="frame" src=""></iframe>

    <script>
        document.getElementById('frame').src = window.location.protocol + '//' + window.location.hostname + ':82';
        
        function switchTab(bot, element) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            element.classList.add('active');
            
            const frame = document.getElementById('frame');
            if (bot === 'xrp') {
                frame.src = window.location.protocol + '//' + window.location.hostname + ':82';
            } else {
                frame.src = window.location.protocol + '//' + window.location.hostname + ':81';
            }
        }
    </script>
</body>
</html>
HTML

cat << 'NGINX' > /etc/nginx/sites-available/default
server {
    listen 80 default_server;
    root /var/www/master_ui;
    index index.html;
    server_name _;
}
server {
    listen 82;
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

sed -i 's/\\\$uri/\$uri/g' /etc/nginx/sites-available/default
ufw allow 82 || true
systemctl restart nginx
