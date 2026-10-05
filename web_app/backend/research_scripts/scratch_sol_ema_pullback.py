import pandas as pd
import numpy as np
import sys, os
sys.path.insert(0, os.path.abspath(".agents/skills/honest-backtest/scripts"))
import bt_data

def run():
    print("Loading SOLUSDT 1m data...")
    df = bt_data.load("SOLUSDT", "1m")
    df.set_index(pd.to_datetime(df['time'], unit='s'), inplace=True)
    B = df.resample('4h').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'}).dropna()
    c = B["close"].values; h = B["high"].values; l = B["low"].values
    dts = B.index
    
    ema200 = B["close"].ewm(span=200, adjust=False).mean().values
    
    tp_pct = 12.0 # RR 12
    sl_pct = 1.0
    
    trades = []
    in_pos = False; tp_price = 0; sl_price = 0; entry_time = None
    
    for i in range(200, len(B)-1):
        if not in_pos:
            # Uptrend (Giá trên EMA200 một đoạn xa > 2%), đột ngột sập chạm lại EMA200
            if c[i-10] > ema200[i-10] * 1.02 and l[i] <= ema200[i] and c[i] > ema200[i]:
                in_pos = True
                entry_p = c[i]
                entry_time = dts[i]
                tp_price = entry_p * (1 + tp_pct/100)
                sl_price = entry_p * (1 - sl_pct/100)
        else:
            if l[i] <= sl_price:
                trades.append({'Lãi/Lỗ': -1}); in_pos = False
            elif h[i] >= tp_price:
                trades.append({'Lãi/Lỗ': 12}); in_pos = False

    df_res = pd.DataFrame(trades)
    wins = len(df_res[df_res['Lãi/Lỗ'] > 0]) if len(df_res) > 0 else 0
    losses = len(df_res[df_res['Lãi/Lỗ'] <= 0]) if len(df_res) > 0 else 0
    print(f"Tổng Lệnh: {len(df_res)} | Thắng: {wins} | Thua: {losses} | Lãi ròng: +{df_res['Lãi/Lỗ'].sum() if len(df_res)>0 else 0} R")

run()
