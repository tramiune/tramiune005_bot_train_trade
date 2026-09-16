from datetime import datetime, timedelta, timezone
import pandas as pd
import numpy as np
from server.main import _fetch_ohlcv_ccxt, _sma, _ema

def analyze_2d():
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
            i += 10
        else:
            i += 1
            
    print(f"Found {len(entries)} entry signals.")
    
    sl_pcts = [0.5, 1.0, 2.0, 3.0, 5.0, 10.0]
    tp_pcts = [0.5, 1.0, 1.5, 2.0, 3.0, 5.0, 10.0]
    
    results = []
    
    for sl_pct in sl_pcts:
        for tp_pct in tp_pcts:
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
                    
                if result == "WIN": wins += 1
                elif result == "LOSS": losses += 1
                    
            ratio = (wins / losses) if losses > 0 else float('inf')
            net_profit = (wins * rr) - losses
            winrate = wins / (wins + losses) * 100 if (wins + losses) > 0 else 0
            
            results.append({
                "SL": sl_pct,
                "TP": tp_pct,
                "RR": rr,
                "Wins": wins,
                "Losses": losses,
                "Ratio": ratio,
                "Winrate": winrate,
                "Profit": net_profit
            })
                
    # Sort by Winrate first to show highest winrate options
    results.sort(key=lambda x: x["Winrate"], reverse=True)
    
    print("\n--- TOP STRATEGIES BY WINRATE ---")
    for r in results[:10]:
        print(f"SL: {r['SL']:>4.1f}% | TP: {r['TP']:>4.1f}% | RR: {r['RR']:>4.2f} | Wins: {r['Wins']:>2} | Losses: {r['Losses']:>2} | Ratio: {r['Ratio']:.2f} | WR: {r['Winrate']:>5.1f}% | Profit: {r['Profit']:+6.2f}R")

if __name__ == "__main__":
    analyze_2d()
