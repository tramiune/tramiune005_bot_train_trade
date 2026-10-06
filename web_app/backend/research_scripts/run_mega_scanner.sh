#!/bin/bash
COINS="BTCUSDT ETHUSDT SOLUSDT XRPUSDT DOGEUSDT BNBUSDT ADAUSDT MATICUSDT LINKUSDT DOTUSDT AVAXUSDT NEARUSDT ATOMUSDT LTCUSDT BCHUSDT"
echo "Bắt đầu tải dữ liệu (Background)..."
for coin in $COINS; do
    echo "Đang kiểm tra và tải $coin..."
    # Lờ đi lỗi nếu dữ liệu đã tồn tại
    python .agents/skills/honest-backtest/scripts/bt_data.py $coin 1m 2022-09 || true
done

echo "Dữ liệu đã sẵn sàng. Bắt đầu chạy Máy quét Tối ưu hóa (Optimizer)..."
python web_app/backend/research_scripts/scratch_top20_optimizer.py
echo "HOÀN THÀNH!"
