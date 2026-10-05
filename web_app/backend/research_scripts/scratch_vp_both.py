import asyncio
import pandas as pd
import numpy as np
import sys, os
sys.path.insert(0, os.path.abspath(".agents/skills/honest-backtest/scripts"))
import bt_data

def run():
    df = bt_data.load("DOGEUSDT", "1m")
    df.set_index(pd.to_datetime(df['time'], unit='s'), inplace=True)
    
    B = df.resample('15min').agg({
        'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
    }).dropna()
    
    c, h, l, v = B["close"].values, B["high"].values, B["low"].values, B["volume"].values
    dts = B.index
    opens = B["open"].values
    
    window = 200 # 2 days POC
    prices = (h + l + c) / 3
    pocs = np.zeros(len(B))
    
    for i in range(window, len(B)):
        p = prices[i-window:i]
        vol = v[i-window:i]
        hist, bins = np.histogram(p, bins=20, weights=vol)
        max_idx = np.argmax(hist)
        pocs[i] = (bins[max_idx] + bins[max_idx+1]) / 2
        
    trades = []
    in_pos = False
    tp_price = 0; sl_price = 0; entry_p = 0; entry_time = None; side = 0
    fee = 0.05 / 100
    RR = 2.0
    
    # Cầu dao vĩ mô Khung 1 Ngày (1920 nến 15m)
    ema_1d = B["close"].ewm(span=1920, adjust=False).mean().values
    
    for i in range(window, len(B)-1):
        if not in_pos:
            if pocs[i] > 0:
                # --- ĐÁNH LONG (Uptrend) ---
                if c[i] > ema_1d[i]:
                    # Giá nến trước nằm trên POC, nến này thọc râu xuống chạm POC
                    if c[i-1] > pocs[i] * 1.005 and l[i] <= pocs[i]:
                        in_pos = True
                        side = 1 # LONG
                        entry_p = opens[i+1]
                        entry_time = dts[i+1]
                        sl_price = entry_p * 0.98
                        dist = entry_p - sl_price
                        tp_price = entry_p + (RR * dist)
                
                # --- ĐÁNH SHORT (Downtrend) ---
                elif c[i] < ema_1d[i]:
                    # Giá nến trước nằm dưới POC, nến này giật râu lên chạm POC
                    if c[i-1] < pocs[i] * 0.995 and h[i] >= pocs[i]:
                        in_pos = True
                        side = -1 # SHORT
                        entry_p = opens[i+1]
                        entry_time = dts[i+1]
                        sl_price = entry_p * 1.02
                        dist = sl_price - entry_p
                        tp_price = entry_p - (RR * dist)
        else:
            if side == 1: # Đang ôm LONG
                if l[i] <= sl_price:
                    trades.append({'time': entry_time, 'exit': dts[i], 'side': 'LONG', 'pnl': -2.0 - fee*200})
                    in_pos = False
                elif h[i] >= tp_price:
                    trades.append({'time': entry_time, 'exit': dts[i], 'side': 'LONG', 'pnl': 4.0 - fee*200})
                    in_pos = False
            elif side == -1: # Đang ôm SHORT
                if h[i] >= sl_price:
                    trades.append({'time': entry_time, 'exit': dts[i], 'side': 'SHORT', 'pnl': -2.0 - fee*200})
                    in_pos = False
                elif l[i] <= tp_price:
                    trades.append({'time': entry_time, 'exit': dts[i], 'side': 'SHORT', 'pnl': 4.0 - fee*200})
                    in_pos = False
                
    res_df = pd.DataFrame(trades)
    res_df['year'] = res_df['exit'].dt.year
    res_df['month'] = res_df['exit'].dt.month
    
    wr = (res_df['pnl']>0).mean() * 100
    print("=== VOLUME PROFILE 15M (ĐÁNH 2 CHIỀU) ===")
    print(f"Tổng Lệnh: {len(res_df)} | Win Rate: {wr:.2f}% | Lãi Ròng: {res_df['pnl'].sum():.2f}%\n")
    
    monthly = res_df.groupby(['year', 'month']).agg(
        trades=('pnl', 'count'),
        wins=('pnl', lambda x: (x > 0).sum()),
        pnl=('pnl', 'sum')
    ).reset_index()
    
    print("Năm-Tháng | Lệnh | Thắng | Win Rate | PnL ròng")
    print("-" * 50)
    for _, row in monthly.iterrows():
        wrate = (row['wins'] / row['trades']) * 100 if row['trades'] > 0 else 0
        print(f"{int(row['year'])}-{int(row['month']):02d}    | {int(row['trades']):4d} | {int(row['wins']):4d}  |   {wrate:5.1f}% | {row['pnl']:6.2f}%")
        
    print("\n--- TỔNG KẾT THEO NĂM ---")
    yearly = res_df.groupby('year').agg(
        trades=('pnl', 'count'),
        wins=('pnl', lambda x: (x > 0).sum()),
        pnl=('pnl', 'sum')
    ).reset_index()
    for _, row in yearly.iterrows():
        wrate = (row['wins'] / row['trades']) * 100 if row['trades'] > 0 else 0
        print(f"{int(row['year'])} | {int(row['trades']):4d} | {int(row['wins']):4d}  |   {wrate:5.1f}% | {row['pnl']:6.2f}%")

run()
