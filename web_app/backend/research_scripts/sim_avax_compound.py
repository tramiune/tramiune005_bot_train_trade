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
    
    # Store all trades R multiplier in sequence
    r_sequence = []
    
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
                        r_sequence.append(profit_R)
                        i = j
                        break
                    j += 1
        i += 1

    # SIMULATION 1: 10 Million VND, 5% Risk per trade
    initial_cap = 10_000_000
    risk_pct = 0.05
    cap = initial_cap
    max_cap = initial_cap
    max_dd_pct = 0
    
    for r in r_sequence:
        risk_amount = cap * risk_pct
        profit_cash = risk_amount * r
        cap += profit_cash
        
        if cap > max_cap:
            max_cap = cap
        
        dd_pct = (max_cap - cap) / max_cap * 100
        if dd_pct > max_dd_pct:
            max_dd_pct = dd_pct

    # SIMULATION 2: 30 Million VND, 4% Risk per trade (from their previous prompt)
    initial_cap_2 = 30_000_000
    risk_pct_2 = 0.04
    cap_2 = initial_cap_2
    
    for r in r_sequence:
        risk_amount = cap_2 * risk_pct_2
        profit_cash = risk_amount * r
        cap_2 += profit_cash

    print(f"Total Trades: {len(r_sequence)}")
    print(f"Total Net R: +{sum(r_sequence):.2f} R")
    print(f"--- SIMULATION 10 MILLION (5% Risk) ---")
    print(f"Final Capital: {cap:,.0f} VND")
    print(f"Multiplier: x{cap / initial_cap:.2f}")
    print(f"Max Drawdown: -{max_dd_pct:.2f}%")
    
    print(f"--- SIMULATION 30 MILLION (4% Risk) ---")
    print(f"Final Capital: {cap_2:,.0f} VND")
    print(f"Multiplier: x{cap_2 / initial_cap_2:.2f}")

if __name__ == "__main__":
    run_analysis()
