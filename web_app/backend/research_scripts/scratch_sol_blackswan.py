import pandas as pd
import numpy as np
import sys, os
sys.path.insert(0, os.path.abspath(".agents/skills/honest-backtest/scripts"))
import bt_data

def run():
    print("Loading SOLUSDT 1m data...")
    df = bt_data.load("SOLUSDT", "1m")
    df.set_index(pd.to_datetime(df['time'], unit='s'), inplace=True)
    B = df.resample('4h').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'}).dropna()
    c = B["close"].values; h = B["high"].values; l = B["low"].values
    dts = B.index
    
    delta = pd.Series(c).diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    rsi = rsi.values
    
    trades = []
    in_pos = False; tp_price = 0; sl_price = 0; entry_time = None
    
    for i in range(20, len(B)-1):
        if not in_pos:
            if rsi[i] < 20.0:
                in_pos = True
                entry_p = c[i]
                entry_time = dts[i]
                tp_price = entry_p * (1 + 24.0/100)
                sl_price = entry_p * (1 - 2.0/100)
        else:
            if l[i] <= sl_price:
                trades.append({'Lãi/Lỗ': -1})
                in_pos = False
            elif h[i] >= tp_price:
                trades.append({'Lãi/Lỗ': 12})
                in_pos = False

    df_res = pd.DataFrame(trades)
    wins = len(df_res[df_res['Lãi/Lỗ'] > 0]) if len(df_res) > 0 else 0
    losses = len(df_res[df_res['Lãi/Lỗ'] <= 0]) if len(df_res) > 0 else 0
    pnl = df_res['Lãi/Lỗ'].sum() if len(df_res) > 0 else 0
    
    print(f"RSI < 20: {len(df_res)} lệnh | Thắng {wins} | Thua {losses} | Lãi ròng {pnl}R")

run()
