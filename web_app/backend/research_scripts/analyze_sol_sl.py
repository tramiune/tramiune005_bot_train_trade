from datetime import datetime, timedelta, timezone
import pandas as pd
import numpy as np
from server.main import _fetch_ohlcv_ccxt, _sma, _ema

def analyze_sol_sl():
    print("Fetching 1 year of 5m data for SOL/USDT...")
    since = datetime.now(timezone.utc) - timedelta(days=365)
    df = _fetch_ohlcv_ccxt("binance", "SOL/USDT", "5m", since=since, limit=120000)
    
    close = df["close"].astype(float)
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    vol = df["volume"].astype(float)
    
    e800 = _ema(close, 800)
    v50 = _sma(vol, 50)
    sma20 = _sma(close, 20)
    std20 = close.rolling(20).std()
    bb_lower = sma20 - 2.5 * std20
    
    # Pre-calculate entry signals to ensure exactly the same trades
    entries = []
    i = 805
    while i < len(df) - 1:
        c = float(close.iloc[i])
        h = float(high.iloc[i])
        l = float(low.iloc[i])
        v = float(vol.iloc[i])
        v_ma = float(v50.iloc[i]) if pd.notna(v50.iloc[i]) else 0
        b_low = float(bb_lower.iloc[i]) if pd.notna(bb_lower.iloc[i]) else 0
        e8 = float(e800.iloc[i]) if pd.notna(e800.iloc[i]) else 0
        
        vol_mult = v / v_ma if v_ma > 0 else 0
        candle_range = h - l
        close_pct = (c - l) / candle_range if candle_range > 0 else 0
        
        if c > e8 and l < b_low and vol_mult > 4.0 and close_pct > 0.7:
            entries.append(i)
            # Skip ahead to avoid multiple entries in the same cluster
            i += 10
        else:
            i += 1
            
    print(f"Found {len(entries)} identical entry signals on SOL.")
    
    sl_pcts = [0.3, 0.5, 0.8, 1.0, 1.2, 1.5, 2.0, 3.0]
    tp_pct = 10.0
    
    print(f"\n--- OPTIMIZING FIXED SL (TP Fixed at 10.0%) ---")
    
    for sl_pct in sl_pcts:
        sl_frac = sl_pct / 100.0
        tp_frac = tp_pct / 100.0
        rr = tp_pct / sl_pct
        
        wins = 0
        losses = 0
        
        for entry_idx in entries:
            entry_price = float(close.iloc[entry_idx])
            sl_price = entry_price * (1 - sl_frac)
            tp_price = entry_price * (1 + tp_frac)
            
            j = entry_idx + 1
            result = None
            
            while j < len(df):
                hi = float(high.iloc[j])
                lo = float(low.iloc[j])
                
                if lo <= sl_price: 
                    result = "LOSS"
                    break
                if hi >= tp_price: 
                    result = "WIN"
                    break
                j += 1
                
            if result == "WIN":
                wins += 1
            elif result == "LOSS":
                losses += 1
                
        total = wins + losses
        if total > 0:
            winrate = wins / total * 100
            net_profit = (wins * rr) - losses
            print(f"SL: {sl_pct:.1f}% | RR: {rr:.1f} | Wins: {wins} | Losses: {losses} | Winrate: {winrate:05.2f}% | Net Profit: {net_profit:+.2f}R")

if __name__ == "__main__":
    analyze_sol_sl()
