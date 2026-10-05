import pandas as pd
import numpy as np
import sys, os
sys.path.insert(0, os.path.abspath(".agents/skills/honest-backtest/scripts"))
import bt_data

def run():
    print("Loading DOGE 1m data...")
    df = bt_data.load("DOGEUSDT", "1m")
    df.set_index(pd.to_datetime(df['time'], unit='s'), inplace=True)
    
    print("Resampling to 4H...")
    B = df.resample('4h').agg({
        'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'
    }).dropna()
    
    c = B["close"].values
    h = B["high"].values
    l = B["low"].values
    dts = B.index
    
    period = 100
    highest = pd.Series(h).rolling(period).max().shift(1).values
    lowest = pd.Series(l).rolling(period).min().shift(1).values
    
    tp_pct = 30.0 # RR 15
    sl_pct = 2.0  # Risk 2%
    fee = 0.05 / 100
    
    trades = []
    in_pos = False
    tp_price = 0; sl_price = 0; entry_time = None
    side = 0
    
    print("Săn Breakout Đỉnh/Đáy 16 Ngày (RR 1:15)...")
    for i in range(period, len(B)-1):
        if not in_pos:
            if c[i] > highest[i]:
                in_pos = True
                side = 1
                entry_p = c[i]
                entry_time = dts[i]
                tp_price = entry_p * (1 + tp_pct/100)
                sl_price = entry_p * (1 - sl_pct/100)
            elif c[i] < lowest[i]:
                in_pos = True
                side = -1
                entry_p = c[i]
                entry_time = dts[i]
                tp_price = entry_p * (1 - tp_pct/100)
                sl_price = entry_p * (1 + sl_pct/100)
        else:
            if side == 1:
                if l[i] <= sl_price:
                    trades.append({'time': entry_time, 'Lãi/Lỗ': -1})
                    in_pos = False
                elif h[i] >= tp_price:
                    trades.append({'time': entry_time, 'Lãi/Lỗ': 15})
                    in_pos = False
            else:
                if h[i] >= sl_price:
                    trades.append({'time': entry_time, 'Lãi/Lỗ': -1})
                    in_pos = False
                elif l[i] <= tp_price:
                    trades.append({'time': entry_time, 'Lãi/Lỗ': 15})
                    in_pos = False

    df_res = pd.DataFrame(trades)
    
    if len(df_res) == 0:
        print("Không có lệnh nào!")
        return
        
    wins = len(df_res[df_res['Lãi/Lỗ'] > 0])
    losses = len(df_res[df_res['Lãi/Lỗ'] <= 0])
    
    print("\n" + "="*60)
    print("🚀 DOGE 4H - DONCHIAN TREND SNIPER (RR 1 ĂN 15)")
    print("="*60)
    print(f"Tổng Lệnh (4 Năm): {len(df_res)} lệnh")
    print(f"Lệnh Thắng: {wins} | Lệnh Thua: {losses}")
    print(f"Win Rate: {wins/len(df_res)*100:.1f}%")
    print(f"Lợi nhuận ròng: +{df_res['Lãi/Lỗ'].sum()} R")

run()
