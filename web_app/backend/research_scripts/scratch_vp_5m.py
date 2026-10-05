import asyncio
import pandas as pd
import numpy as np
import time
import sys, os
sys.path.insert(0, os.path.abspath(".agents/skills/honest-backtest/scripts"))
import bt_data

def run():
    print("Loading DOGE 1m data...")
    df = bt_data.load("DOGEUSDT", "1m")
    df.set_index(pd.to_datetime(df['time'], unit='s'), inplace=True)
    
    print("Resampling to 5m...")
    B = df.resample('5min').agg({
        'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
    }).dropna()
    
    c, h, l, v = B["close"].values, B["high"].values, B["low"].values, B["volume"].values
    opens = B["open"].values
    dts = B.index
    
    # Window 2 ngày trên khung 5m = 2 * 24 * 12 = 576 nến
    window = 576
    prices = (h + l + c) / 3
    pocs = np.zeros(len(B))
    
    print("Tính toán Volume Profile 5m...")
    for i in range(window, len(B)):
        p = prices[i-window:i]
        vol = v[i-window:i]
        hist, bins = np.histogram(p, bins=30, weights=vol) # Tăng độ mượt với 30 bins
        max_idx = np.argmax(hist)
        pocs[i] = (bins[max_idx] + bins[max_idx+1]) / 2
        
    # Trend Mẹ (20 Ngày) trên khung 5m = 20 * 24 * 12 = 5760 nến
    ema_20d = B["close"].ewm(span=5760, adjust=False).mean().values
    
    trades = []
    in_pos = False
    tp_price = 0; sl_price = 0; entry_p = 0; entry_time = None
    fee = 0.05 / 100
    RR = 2.0
    
    for i in range(window, len(B)-1):
        if not in_pos:
            if pocs[i] > 0 and c[i] > ema_20d[i]:
                # Giá trước đó nằm trên POC, giá hiện tại chọt xuống chạm vạch POC
                if c[i-1] > pocs[i] * 1.002 and l[i] <= pocs[i]:
                    in_pos = True
                    entry_p = opens[i+1] # Bắt đầu ở cây nến sau (Tương đương kê Limit khớp)
                    entry_time = dts[i+1]
                    
                    sl_price = entry_p * 0.98
                    dist = entry_p - sl_price
                    tp_price = entry_p + (RR * dist)
        else:
            if l[i] <= sl_price:
                trades.append({'time': entry_time, 'exit': dts[i], 'pnl': -2.0 - fee*200})
                in_pos = False
            elif h[i] >= tp_price:
                trades.append({'time': entry_time, 'exit': dts[i], 'pnl': 4.0 - fee*200})
                in_pos = False
                
    res_df = pd.DataFrame(trades)
    res_df['year'] = res_df['exit'].dt.year
    
    wr = (res_df['pnl']>0).mean() * 100
    print(f"\n=== VOLUME PROFILE BẮT POC (DOGE 5M) ===")
    print(f"R:R = 1:2 (SL 2%, TP 4%)")
    print(f"Tổng Lệnh: {len(res_df)} | Win Rate: {wr:.2f}% | Lãi Ròng: {res_df['pnl'].sum():.2f}%")
    
    yearly = res_df.groupby('year').agg(
        trades=('pnl', 'count'),
        wins=('pnl', lambda x: (x > 0).sum()),
        pnl=('pnl', 'sum')
    ).reset_index()
    
    print("\nNăm  | Lệnh | Thắng | Win Rate | PnL ròng")
    for _, row in yearly.iterrows():
        wrate = (row['wins'] / row['trades']) * 100 if row['trades'] > 0 else 0
        print(f"{int(row['year'])} | {int(row['trades']):4d} | {int(row['wins']):4d}  |   {wrate:5.1f}% | {row['pnl']:6.2f}%")

run()
