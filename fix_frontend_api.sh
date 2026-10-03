#!/bin/bash
cd /root/tramiune005_bot_train_trade/web_app/frontend/src

sed -i 's/:8000//g' App.tsx
sed -i 's/:8000//g' components/ChartWidget.tsx
sed -i 's/:8000//g' components/ControlPanel.tsx
sed -i 's/:8000//g' components/TradeHistory.tsx

cd ..
npm run build
cp -r dist/* /var/www/html/ 2>/dev/null || true
