import pandas as pd
import numpy as np
import sys, os
sys.path.insert(0, os.path.abspath(".agents/skills/honest-backtest/scripts"))
import bt_data
import mplfinance as mpf
import datetime

# Tải dữ liệu DOGE 15m
df = bt_data.load("DOGEUSDT", "1m")
df.set_index(pd.to_datetime(df['time'], unit='s'), inplace=True)
B = df.resample('15min').agg({
    'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
}).dropna()

# Tìm một đoạn Uptrend rực rỡ của DOGE: Đầu tháng 3 năm 2024
start_date = '2024-02-28 00:00:00'
end_date = '2024-03-01 12:00:00'
subset = B.loc[start_date:end_date].copy()

# Rename columns cho mplfinance
subset = subset.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'})

# Tìm các điểm Support và Cấu trúc
# Ở đây ta sẽ chỉ plot chart đơn thuần và lưu ra file ảnh, sau đó ta tự annotate (hoặc chỉ cần vẽ đường)
# Chúng ta có thể dùng mplfinance addplot để vẽ mũi tên, hoặc dùng hlines để vẽ kháng cự hỗ trợ.

# Vẽ đường hỗ trợ giả định tại mốc 0.113
# Vẽ điểm Entry Breakout giả định tại 0.120

save_path = "/Users/finn/.gemini/antigravity/brain/921139ef-edbf-43e7-bf4e-d052df21201b/scratch/doge_setup_example.png"

# Setup lines
hlines = dict(hlines=[0.1135, 0.1215], colors=['r', 'g'], linestyle='--', linewidths=[2, 2])

mpf.plot(subset, type='candle', volume=True, style='charles',
         title="DOGE/USDT 15m: Market Structure Shift (Setup Video)",
         hlines=hlines,
         savefig=save_path,
         figratio=(16,9), figscale=1.5)
         
print(f"Chart saved to {save_path}")
