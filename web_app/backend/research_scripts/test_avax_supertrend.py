import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from datetime import datetime, timedelta, timezone
import pandas as pd
import numpy as np
from server.main import _fetch_ohlcv_ccxt, _atr

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
        # Final Upper Band
        if basic_ub.iloc[i] < final_ub[i-1] or close[i-1] > final_ub[i-1]:
            final_ub[i] = basic_ub.iloc[i]
        else:
            final_ub[i] = final_ub[i-1]
            
        # Final Lower Band
        if basic_lb.iloc[i] > final_lb[i-1] or close[i-1] < final_lb[i-1]:
            final_lb[i] = basic_lb.iloc[i]
        else:
            final_lb[i] = final_lb[i-1]
            
        # Supertrend direction
        if supertrend[i-1] == 1 and close[i] < final_lb[i]:
            supertrend[i] = -1
        elif supertrend[i-1] == -1 and close[i] > final_ub[i]:
            supertrend[i] = 1
        elif supertrend[i-1] == 0:
            supertrend[i] = 1 if close[i] > final_ub[i] else -1
        else:
            supertrend[i] = supertrend[i-1]
            
    df['st'] = supertrend
    df['ub'] = final_ub
    df['lb'] = final_lb
    return df

def run_analysis():
    print("Fetching 4 years of 1h data for AVAX...")
    since = datetime.now(timezone.utc) - timedelta(days=1460)
    raw_df = _fetch_ohlcv_ccxt("binance", "AVAX/USDT", "1h", since=since, limit=100000)
    
    print("\n--- AVAX SUPERTREND (LONG ONLY, FIXED RR) ---")
    for mult in [2.0, 3.0, 4.0]:
        df = get_supertrend(raw_df.copy(), period=10, multiplier=mult)
        
        trades = []
        i = 50
        while i < len(df) - 1:
            # Signal: ST flips to 1
            if df['st'].iloc[i-1] == -1 and df['st'].iloc[i] == 1:
                entry = float(df['close'].iloc[i])
                sl = float(df['lb'].iloc[i])
                
                risk = entry - sl
                if risk > 0:
                    tp = entry + 3.0 * risk # Testing RR 3.0
                    
                    j = i + 1
                    exit_idx = None
                    result = None
                    while j < len(df):
                        if float(df['low'].iloc[j]) <= sl:
                            exit_idx, result = j, "LOSS"
                            break
                        if float(df['high'].iloc[j]) >= tp:
                            exit_idx, result = j, "WIN"
                            break
                        j += 1
                        
                    if exit_idx is not None:
                        trades.append(result)
                        i = exit_idx
                        continue
            i += 1
            
        wins = trades.count("WIN")
        losses = trades.count("LOSS")
        total = len(trades)
        wr = wins / total * 100 if total else 0
        net = wins * 3.0 - losses
        print(f"Mult {mult:>3.1f} (RR 3.0) | Trades: {total:>3} | Wins: {wins:>3} | Losses: {losses:>3} | WR: {wr:05.2f}% | Profit: {net:>+6.1f} R")
        
    print("\n--- AVAX SUPERTREND (LONG ONLY, TRAILING STOP) ---")
    # Instead of fixed TP/SL, we hold until Supertrend flips back to -1
    for mult in [2.0, 3.0, 4.0]:
        df = get_supertrend(raw_df.copy(), period=10, multiplier=mult)
        
        trades = []
        profit_R_total = 0.0
        i = 50
        while i < len(df) - 1:
            if df['st'].iloc[i-1] == -1 and df['st'].iloc[i] == 1:
                entry = float(df['close'].iloc[i])
                initial_risk = entry - float(df['lb'].iloc[i])
                
                if initial_risk > 0:
                    j = i + 1
                    exit_idx = None
                    exit_price = 0
                    while j < len(df):
                        # Exit when ST flips to -1 (using close price of the flip candle)
                        if df['st'].iloc[j] == -1:
                            exit_idx = j
                            exit_price = float(df['close'].iloc[j])
                            break
                        j += 1
                        
                    if exit_idx is not None:
                        profit_cash = exit_price - entry
                        profit_R = profit_cash / initial_risk
                        
                        trades.append({"result": "WIN" if profit_R > 0 else "LOSS", "R": profit_R})
                        i = exit_idx
                        continue
            i += 1
            
        wins = len([t for t in trades if t["result"] == "WIN"])
        losses = len([t for t in trades if t["result"] == "LOSS"])
        total = len(trades)
        wr = wins / total * 100 if total else 0
        net_R = sum([t["R"] for t in trades])
        print(f"Mult {mult:>3.1f} (Trailing) | Trades: {total:>3} | Wins: {wins:>3} | Losses: {losses:>3} | WR: {wr:05.2f}% | Profit: {net_R:>+6.1f} R")

if __name__ == "__main__":
    run_analysis()
