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
    
    print("Resampling to 15m...")
    B = df.resample('15min').agg({
        'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
    }).dropna()
    
    c, h, l, v = B["close"].values, B["high"].values, B["low"].values, B["volume"].values
    dts = B.index
    opens = B["open"].values
    
    print("Calculating Rolling Volume Profile (POC)... this takes ~3 seconds")
    t0 = time.time()
    
    # We use a 200-candle rolling window (~ 2 days)
    window = 200
    prices = (h + l + c) / 3
    pocs = np.zeros(len(B))
    
    # Calculate POC (Point of Control) for each window
    for i in range(window, len(B)):
        p = prices[i-window:i]
        vol = v[i-window:i]
        # We split the price range of the last 200 candles into 20 bins
        hist, bins = np.histogram(p, bins=20, weights=vol)
        # The bin with max volume is the POC
        max_idx = np.argmax(hist)
        pocs[i] = (bins[max_idx] + bins[max_idx+1]) / 2
        
    print(f"POC calculated in {time.time()-t0:.2f}s")
    
    # --- STRATEGY LOGIC ---
    # We want to buy the dip when price pulls back to the POC
    trades = []
    in_pos = False
    tp_price = 0; sl_price = 0; entry_p = 0; entry_time = None
    fee = 0.05 / 100
    RR = 2.0
    
    ema_1d = B["close"].ewm(span=1920, adjust=False).mean().values
    
    for i in range(window, len(B)-1):
        if not in_pos:
            # Check if we touch POC from above
            # We must be in a macro uptrend (c[i] > ema_1d[i])
            # The POC must be established (pocs[i] > 0)
            if pocs[i] > 0 and c[i] > ema_1d[i]:
                # Pullback condition: Previous close was above POC, current low pierces POC
                if c[i-1] > pocs[i] * 1.005 and l[i] <= pocs[i]:
                    # We enter LONG
                    in_pos = True
                    entry_p = opens[i+1]
                    entry_time = dts[i+1]
                    
                    # Stop loss placed 2% below entry
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
                
    if len(trades) == 0:
        print("No trades")
        return
        
    res_df = pd.DataFrame(trades)
    res_df['year'] = res_df['exit'].dt.year
    
    wr = (res_df['pnl']>0).mean() * 100
    print(f"\n=== VOLUME PROFILE BẮT POC (DOGE 15M) ===")
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
