import pandas as pd
import numpy as np
import sys, os
sys.path.insert(0, os.path.abspath(".agents/skills/honest-backtest/scripts"))
import bt_data
import mplfinance as mpf
import datetime

df = bt_data.load("DOGEUSDT", "1m")
df.set_index(pd.to_datetime(df['time'], unit='s'), inplace=True)
B = df.resample('15min').agg({
    'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
}).dropna()

# Example 2: November 2024 massive rally
start_date = '2024-11-06 00:00:00'
end_date = '2024-11-08 12:00:00'
subset = B.loc[start_date:end_date].copy()

subset = subset.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'})

save_path = "/Users/finn/.gemini/antigravity/brain/921139ef-edbf-43e7-bf4e-d052df21201b/example2.png"

# Setup lines for Nov 6-8
# Support around 0.186, Breakout around 0.198
hlines = dict(hlines=[0.186, 0.198], colors=['r', 'g'], linestyle='--', linewidths=[2, 2])

mpf.plot(subset, type='candle', volume=True, style='charles',
         title="DOGE/USDT 15m: Market Structure Shift (Nov 2024)",
         hlines=hlines,
         savefig=save_path,
         figratio=(16,9), figscale=1.5)
         
print(f"Chart 2 saved")
