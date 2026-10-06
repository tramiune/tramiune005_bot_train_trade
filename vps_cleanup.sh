#!/bin/bash
set -e

echo "=== STARTING VPS DISK CLEANUP ==="
echo "Disk before cleanup:"
df -h /

# 1. Clean systemd journal logs (keep last 2 days)
echo "1. Vacuuming journal logs..."
journalctl --vacuum-time=2d || true

# 2. Clean APT cache and orphaned packages
echo "2. Cleaning apt packages..."
apt-get clean
apt-get autoremove -y

# 3. Clean pip and npm caches
echo "3. Cleaning pip and npm caches..."
pip cache purge 2>/dev/null || true
npm cache clean --force 2>/dev/null || true
rm -rf /root/.cache/pip /root/.npm 2>/dev/null || true

# 4. Remove old Google Chrome caches and old downloads
echo "4. Removing old browser caches and downloads..."
rm -rf /root/.cache/google-chrome /root/.config/google-chrome || true
rm -rf /root/Downloads/* || true

# 5. Remove old duplicate repository (tramiune005_bot_train_trade)
# Note: bot-xrp is at /root/bot_xrp and bot-sol is at /root/bot_sol
if [ -d "/root/tramiune005_bot_train_trade" ]; then
    echo "5. Removing old duplicate repository folder..."
    rm -rf /root/tramiune005_bot_train_trade
fi

# 6. Clean PM2 logs flush
echo "6. Flushing PM2 logs..."
pm2 flush || true

echo "=== CLEANUP COMPLETED ==="
echo "Disk after cleanup:"
df -h /

