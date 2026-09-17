import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from datetime import datetime, timedelta, timezone
import pandas as pd
import numpy as np
from server.main import _fetch_ohlcv_ccxt, _atr, _ema

def get_supertrend(df, period=10, multiplier=3.0):
    atr = _atr(df, period)
    hl2 = (df['high'] + df['low']) / 2
    basic_ub = hl2 + multiplier * atr
    basic_lb = hl2 - multiplier * atr
    final_ub = np.zeros(len(df))
    final_lb = np.zeros(len(df))
    supertrend = np.zeros(len(df))
    close = df['close'].values
    for i in range(period, len(df)):
        if basic_ub.iloc[i] < final_ub[i-1] or close[i-1] > final_ub[i-1]: final_ub[i] = basic_ub.iloc[i]
        else: final_ub[i] = final_ub[i-1]
        if basic_lb.iloc[i] > final_lb[i-1] or close[i-1] < final_lb[i-1]: final_lb[i] = basic_lb.iloc[i]
        else: final_lb[i] = final_lb[i-1]
        if supertrend[i-1] == 1 and close[i] < final_lb[i]: supertrend[i] = -1
        elif supertrend[i-1] == -1 and close[i] > final_ub[i]: supertrend[i] = 1
        elif supertrend[i-1] == 0: supertrend[i] = 1 if close[i] > final_ub[i] else -1
        else: supertrend[i] = supertrend[i-1]
    df['st'] = supertrend
    df['ub'] = final_ub
    df['lb'] = final_lb
    return df

def run_analysis():
    since = datetime.now(timezone.utc) - timedelta(days=1460)
    raw_df = _fetch_ohlcv_ccxt("binance", "AVAX/USDT", "1h", since=since, limit=100000)
    raw_df['e200'] = _ema(raw_df['close'].astype(float), 200)
    
    df = get_supertrend(raw_df.copy(), period=10, multiplier=3.0)
    
    winning_r = []
    losing_r = []
    
    i = 205
    while i < len(df) - 1:
        if df['st'].iloc[i-1] == -1 and df['st'].iloc[i] == 1 and df['close'].iloc[i] > df['e200'].iloc[i]:
            entry = float(df['close'].iloc[i])
            initial_risk = entry - float(df['lb'].iloc[i])
            
            if initial_risk > 0:
                j = i + 1
                while j < len(df):
                    if df['st'].iloc[j] == -1:
                        exit_price = float(df['close'].iloc[j])
                        profit_R = (exit_price - entry) / initial_risk
                        if profit_R > 0:
                            winning_r.append(profit_R)
                        else:
                            losing_r.append(profit_R)
                        i = j
                        break
                    j += 1
        i += 1
        
    print(f"Total Wins: {len(winning_r)}")
    print(f"Avg Winning RR: {np.mean(winning_r):.2f}")
    print(f"Max Winning RR: {np.max(winning_r):.2f}")
    print(f"Total Losses: {len(losing_r)}")
    print(f"Avg Losing RR: {np.mean(losing_r):.2f}")

if __name__ == "__main__":
    run_analysis()
