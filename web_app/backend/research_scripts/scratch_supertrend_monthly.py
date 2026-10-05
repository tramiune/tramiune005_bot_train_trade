import asyncio
import pandas as pd
import numpy as np
import sys, os
sys.path.insert(0, os.path.abspath(".agents/skills/honest-backtest/scripts"))
import bt_data

def run():
    df = bt_data.load("DOGEUSDT", "1m")
    df.set_index(pd.to_datetime(df['time'], unit='s'), inplace=True)
    
    B = df.resample('4h').agg({
        'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
    }).dropna()
    
    c, h, l = B["close"].values, B["high"].values, B["low"].values
    dts = B.index
    opens = B["open"].values
    
    length = 10
    multiplier = 3.0
    
    tr1 = h - l
    tr2 = np.abs(h - np.roll(c, 1))
    tr3 = np.abs(l - np.roll(c, 1))
    tr = np.maximum(tr1, np.maximum(tr2, tr3))
    tr[0] = 0
    
    atr = pd.Series(tr).rolling(length).mean().values
    hl2 = (h + l) / 2
    
    upper_band = hl2 + (multiplier * atr)
    lower_band = hl2 - (multiplier * atr)
    
    in_uptrend = np.ones(len(B), dtype=bool)
    super_trend = np.zeros(len(B))
    
    for i in range(1, len(B)):
        if c[i] > upper_band[i-1]:
            in_uptrend[i] = True
        elif c[i] < lower_band[i-1]:
            in_uptrend[i] = False
        else:
            in_uptrend[i] = in_uptrend[i-1]
            if in_uptrend[i] and lower_band[i] < lower_band[i-1]:
                lower_band[i] = lower_band[i-1]
            if not in_uptrend[i] and upper_band[i] > upper_band[i-1]:
                upper_band[i] = upper_band[i-1]
                
    trades = []
    in_pos = False
    entry_p = 0; entry_time = None
    fee = 0.05 / 100
    
    for i in range(length, len(B)-1):
        if not in_pos:
            if not in_uptrend[i-1] and in_uptrend[i]:
                in_pos = True
                entry_p = opens[i+1]
                entry_time = dts[i+1]
        else:
            if in_uptrend[i-1] and not in_uptrend[i]:
                exit_p = opens[i+1]
                pnl_pct = ((exit_p - entry_p) / entry_p) * 100
                trades.append({'time': entry_time, 'exit': dts[i+1], 'pnl': pnl_pct - fee*200})
                in_pos = False
                
    res_df = pd.DataFrame(trades)
    res_df['year'] = res_df['exit'].dt.year
    res_df['month'] = res_df['exit'].dt.month
    
    print("\n=== SAO KÊ CHI TIẾT TỪNG THÁNG: SUPERTREND 4H (DOGE) ===")
    monthly = res_df.groupby(['year', 'month']).agg(
        trades=('pnl', 'count'),
        wins=('pnl', lambda x: (x > 0).sum()),
        pnl=('pnl', 'sum')
    ).reset_index()
    
    print("Năm-Tháng | Lệnh | Thắng | Win Rate | PnL ròng")
    print("-" * 50)
    for _, row in monthly.iterrows():
        wr_m = (row['wins'] / row['trades']) * 100 if row['trades'] > 0 else 0
        print(f"{int(row['year'])}-{int(row['month']):02d}    | {int(row['trades']):4d} | {int(row['wins']):4d}  |   {wr_m:5.1f}% | {row['pnl']:+8.2f}%")

run()
