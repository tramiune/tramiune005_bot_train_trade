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
    
    window = 200
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
    tp_price = 0; sl_price = 0; entry_p = 0; entry_time = None
    fee = 0.05 / 100
    RR = 2.0
    
    ema_1d = B["close"].ewm(span=1920, adjust=False).mean().values
    
    for i in range(window, len(B)-1):
        if not in_pos:
            if pocs[i] > 0 and c[i] > ema_1d[i]:
                if c[i-1] > pocs[i] * 1.005 and l[i] <= pocs[i]:
                    in_pos = True
                    entry_p = opens[i+1]
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
    res_df['month'] = res_df['exit'].dt.month
    
    print("=== VOLUME PROFILE 15M (TỪNG THÁNG) ===")
    monthly = res_df.groupby(['year', 'month']).agg(
        trades=('pnl', 'count'),
        wins=('pnl', lambda x: (x > 0).sum()),
        pnl=('pnl', 'sum')
    ).reset_index()
    
    print("Năm-Tháng | Lệnh | Thắng | Win Rate | PnL ròng")
    print("-" * 50)
    for _, row in monthly.iterrows():
        wr = (row['wins'] / row['trades']) * 100 if row['trades'] > 0 else 0
        print(f"{int(row['year'])}-{int(row['month']):02d}    | {int(row['trades']):4d} | {int(row['wins']):4d}  |   {wr:5.1f}% | {row['pnl']:6.2f}%")
        
run()
