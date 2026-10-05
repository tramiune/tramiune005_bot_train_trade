import asyncio
import pandas as pd
import numpy as np
import sys, os
sys.path.insert(0, os.path.abspath(".agents/skills/honest-backtest/scripts"))
import bt_data

def run():
    df = bt_data.load("DOGEUSDT", "1m")
    df.set_index(pd.to_datetime(df['time'], unit='s'), inplace=True)
    df_15m = df.resample('15min').agg({
        'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
    }).dropna()
    
    B = df_15m
    c, h, l, v = B["close"], B["high"], B["low"], B["volume"]
    
    h_c = h - c.shift()
    l_c = l - c.shift()
    tr = pd.concat([h - l, h_c.abs(), l_c.abs()], axis=1).max(axis=1)
    
    a = tr.rolling(20).mean()
    mid = c.rolling(20).mean()
    sd = c.rolling(20).std()
    
    on = (mid + 2 * sd < mid + 1.5 * a) & (mid - 2 * sd > mid - 1.5 * a)
    dur = on.groupby((~on).cumsum()).cumsum()
    fire = (~on) & on.shift(1, fill_value=False) & (dur.shift(1) >= 5) & (v > 1.5 * v.rolling(20).mean())
    bull = c > mid
    
    sig_follow = np.where(fire, np.where(bull, 1, -1), 0)
    
    opens = B["open"].values
    highs = B["high"].values
    lows = B["low"].values
    dts = B.index
    
    tp_pct = 5.0
    sl_pct = 2.0
    fee = 0.05 / 100
    
    trades = []
    in_pos = False
    tp_price = 0; sl_price = 0; side = 0
    entry_time = None
    
    for i in range(20, len(B)-1):
        if not in_pos:
            if sig_follow[i] != 0:
                in_pos = True
                side = sig_follow[i]
                entry_p = opens[i+1]
                entry_time = dts[i+1]
                if side == 1:
                    tp_price = entry_p * (1 + tp_pct/100)
                    sl_price = entry_p * (1 - sl_pct/100)
                else:
                    tp_price = entry_p * (1 - tp_pct/100)
                    sl_price = entry_p * (1 + sl_pct/100)
        else:
            if side == 1:
                if lows[i] <= sl_price:
                    trades.append({'time': entry_time, 'exit': dts[i], 'pnl': -sl_pct - fee*200})
                    in_pos = False
                elif highs[i] >= tp_price:
                    trades.append({'time': entry_time, 'exit': dts[i], 'pnl': tp_pct - fee*200})
                    in_pos = False
            else:
                if highs[i] >= sl_price:
                    trades.append({'time': entry_time, 'exit': dts[i], 'pnl': -sl_pct - fee*200})
                    in_pos = False
                elif lows[i] <= tp_price:
                    trades.append({'time': entry_time, 'exit': dts[i], 'pnl': tp_pct - fee*200})
                    in_pos = False
                    
    res_df = pd.DataFrame(trades)
    res_df['year'] = res_df['exit'].dt.year
    res_df['month'] = res_df['exit'].dt.month
    
    print("=== DOGE 15M SQUEEZE (FOLLOW, TP 5%, SL 2%) ===")
    
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
        
    yearly = res_df.groupby('year').agg(
        trades=('pnl', 'count'),
        wins=('pnl', lambda x: (x > 0).sum()),
        pnl=('pnl', 'sum')
    ).reset_index()
    
    print("\n--- TỔNG KẾT THEO NĂM ---")
    print("Năm  | Lệnh | Thắng | Win Rate | PnL ròng")
    for _, row in yearly.iterrows():
        wr = (row['wins'] / row['trades']) * 100 if row['trades'] > 0 else 0
        print(f"{int(row['year'])} | {int(row['trades']):4d} | {int(row['wins']):4d}  |   {wr:5.1f}% | {row['pnl']:6.2f}%")
        
run()
