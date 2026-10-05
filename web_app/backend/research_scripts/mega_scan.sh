#!/bin/bash
source web_app/backend/.venv/bin/activate

COINS=("BTCUSDT" "ETHUSDT" "BNBUSDT" "ADAUSDT" "AVAXUSDT" "LINKUSDT" "MATICUSDT" "DOTUSDT" "LTCUSDT" "BCHUSDT" "ATOMUSDT" "UNIUSDT" "FTMUSDT" "NEARUSDT" "ALGOUSDT" "SANDUSDT" "MANAUSDT" "AXSUSDT" "GALAUSDT" "FILUSDT")

# Xóa file artifact cũ nếu có
rm -f /Users/finn/.gemini/antigravity/brain/921139ef-edbf-43e7-bf4e-d052df21201b/top20_coins_optimal.md

echo "# HỒ SƠ TỐI ƯU HÓA 20 ĐỒNG COIN (MEGA SCAN)" > /Users/finn/.gemini/antigravity/brain/921139ef-edbf-43e7-bf4e-d052df21201b/top20_coins_optimal.md
echo "Đang xử lý tải dữ liệu... Bản báo cáo này sẽ cập nhật tự động khi từng đồng coin hoàn tất." >> /Users/finn/.gemini/antigravity/brain/921139ef-edbf-43e7-bf4e-d052df21201b/top20_coins_optimal.md

for coin in "${COINS[@]}"; do
    echo "======================================"
    echo "🚀 BẮT ĐẦU XỬ LÝ COIN: $coin"
    echo "======================================"
    # Tải data (Bỏ qua nếu đã tải)
    python .agents/skills/honest-backtest/scripts/bt_data.py $coin 1m 2022-09
done

echo "======================================"
echo "🎯 ĐÃ TẢI XONG TOÀN BỘ DATA. BẮT ĐẦU SIÊU QUÉT ĐA CHIỀU..."
echo "======================================"

python web_app/backend/scratch_top20_scanner.py

echo "✅ HOÀN TẤT CHIẾN DỊCH!"
