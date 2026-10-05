import asyncio
import pandas as pd
import numpy as np
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
    
    c, h, l, o = B["close"], B["high"], B["low"], B["open"]
    
    # Track the major support level (Lowest low of the past 100 candles, excluding the last 5 to ensure it's a distinct old low)
    # Using pandas rolling min on shifted data
    support = l.shift(5).rolling(100).min()
    
    # Sweep Condition:
    # 1. Low pierces the support
    # 2. But doesn't pierce too deep (max 2%)
    # 3. Close reclaims the support (Close > support)
    pierce = (l < support) & (l >= support * 0.98) & (c > support)
    
    # Require it to close strong (upper 50% of the candle)
    candle_range = h - l
    close_pos = (c - l) / candle_range.replace(0, np.nan)
    fire_long = pierce & (close_pos > 0.5)
    
    sig_long = np.where(fire_long, 1, 0)
    
    opens = B["open"].values
    highs = B["high"].values
    lows = B["low"].values
    dts = B.index
    
    trades = []
    in_pos = False
    tp_price = 0; sl_price = 0; entry_p = 0; entry_time = None
    fee = 0.05 / 100
    
    # We will use Dynamic R:R (e.g. Risk = distance to wick low, Reward = 2 * Risk)
    RR = 2.0
    
    for i in range(150, len(B)-1):
        if not in_pos:
            if sig_long[i] == 1:
                in_pos = True
                entry_p = opens[i+1]
                entry_time = dts[i+1]
                # SL is placed just below the sweep wick
                sl_price = lows[i] * 0.999
                risk = entry_p - sl_price
                if risk <= 0 or (risk / entry_p) > 0.05: # Ignore if risk is negative or > 5%
                    in_pos = False
                    continue
                tp_price = entry_p + (RR * risk)
        else:
            if lows[i] <= sl_price:
                # Loss
                loss_pct = (sl_price - entry_p) / entry_p * 100
                trades.append({'time': entry_time, 'exit': dts[i], 'pnl': loss_pct - fee*200})
                in_pos = False
            elif highs[i] >= tp_price:
                # Win
                win_pct = (tp_price - entry_p) / entry_p * 100
                trades.append({'time': entry_time, 'exit': dts[i], 'pnl': win_pct - fee*200})
                in_pos = False
                
    res_df = pd.DataFrame(trades)
    res_df['year'] = res_df['exit'].dt.year
    res_df['month'] = res_df['exit'].dt.month
    
    print("=== LIQUIDITY SWEEP W-BOTTOM (DOGE 15M) ===")
    print(f"Risk:Reward = 1:{RR}")
    
    monthly = res_df.groupby(['year', 'month']).agg(
        trades=('pnl', 'count'),
        wins=('pnl', lambda x: (x > 0).sum()),
        pnl=('pnl', 'sum')
    ).reset_index()
    
    print("Năm-Tháng | Lệnh | Thắng | Win Rate | PnL ròng (Unleveraged)")
    print("-" * 60)
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
