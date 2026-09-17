import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from datetime import datetime, timedelta, timezone
import pandas as pd
import numpy as np
from server.main import _fetch_ohlcv_ccxt, _atr, _ema, _sma

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
    raw_df['v20'] = _sma(raw_df['volume'].astype(float), 20)
    
    df = get_supertrend(raw_df.copy(), period=10, multiplier=3.0)
    
    trades = []
    r_sequence = []
    i = 205
    while i < len(df) - 1:
        # Signals
        st_flips_bullish = df['st'].iloc[i-1] == -1 and df['st'].iloc[i] == 1
        is_uptrend = df['close'].iloc[i] > df['e200'].iloc[i]
        
        # New Filters
        dt = pd.to_datetime(df['timestamp'].iloc[i], utc=True)
        is_not_sun_mon = dt.dayofweek not in [0, 6] # Exclude 0 (Mon) and 6 (Sun)
        
        v = float(df['volume'].iloc[i])
        v_ma = float(df['v20'].iloc[i]) if pd.notna(df['v20'].iloc[i]) else 0
        has_volume = (v / v_ma) >= 1.5 if v_ma > 0 else False
        
        if st_flips_bullish and is_uptrend and is_not_sun_mon and has_volume:
            entry = float(df['close'].iloc[i])
            initial_risk = entry - float(df['lb'].iloc[i])
            
            if initial_risk > 0:
                j = i + 1
                exit_idx = None
                exit_price = 0
                while j < len(df):
                    if df['st'].iloc[j] == -1:
                        exit_idx = j
                        exit_price = float(df['close'].iloc[j])
                        break
                    j += 1
                    
                if exit_idx is not None:
                    profit_cash = exit_price - entry
                    profit_R = profit_cash / initial_risk
                    trades.append("WIN" if profit_R > 0 else "LOSS")
                    r_sequence.append(profit_R)
                    i = exit_idx
                    continue
        i += 1
        
    wins = trades.count("WIN")
    losses = trades.count("LOSS")
    total = len(trades)
    wr = wins / total * 100 if total else 0
    net_R = sum(r_sequence)
    
    # Compounding Simulation
    initial_cap = 30_000_000
    risk_pct = 0.04
    cap = initial_cap
    max_cap = initial_cap
    max_dd_pct = 0
    
    for r in r_sequence:
        risk_amount = cap * risk_pct
        profit_cash = risk_amount * r
        cap += profit_cash
        if cap > max_cap: max_cap = cap
        dd_pct = (max_cap - cap) / max_cap * 100
        if dd_pct > max_dd_pct: max_dd_pct = dd_pct

    print("\n--- AVAX SUPERTREND V2 (FILTERED) ---")
    print(f"Total Trades: {total}")
    print(f"Wins: {wins}")
    print(f"Losses: {losses}")
    print(f"Winrate: {wr:.2f}%")
    print(f"Net Profit: +{net_R:.2f} R")
    
    print(f"\n--- COMPOUNDING (30M VND, 4% Risk) ---")
    print(f"Final Capital: {cap:,.0f} VND")
    print(f"Net Cash Profit: {cap - initial_cap:,.0f} VND")
    print(f"Max Drawdown: -{max_dd_pct:.2f}%")

if __name__ == "__main__":
    run_analysis()
