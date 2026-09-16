from datetime import datetime, timedelta, timezone
import pandas as pd
import numpy as np
from server.main import _fetch_ohlcv_ccxt, _sma, _ema, _atr

def analyze_eth_god():
    print("Fetching 4 years of 1h data for ETH/USDT...")
    since = datetime.now(timezone.utc) - timedelta(days=1460)
    df = _fetch_ohlcv_ccxt("binance", "ETH/USDT", "1h", since=since, limit=50000)
    
    close = df["close"].astype(float)
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    vol = df["volume"].astype(float)
    
    sma20 = _sma(close, 20)
    std20 = close.rolling(20).std()
    bb_upper = sma20 + 2 * std20
    bb_lower = sma20 - 2 * std20
    
    ema20 = _ema(close, 20)
    atr20 = _atr(df, 20)
    kc_upper = ema20 + 1.5 * atr20
    kc_lower = ema20 - 1.5 * atr20
    
    atr14 = _atr(df, 14)
    v20 = _sma(vol, 20)
    e200 = _ema(close, 200)
    
    is_squeeze = (bb_upper < kc_upper) & (bb_lower > kc_lower)
    
    trades = []
    i = 205
    
    while i < len(df) - 1:
        c = float(close.iloc[i])
        h = float(high.iloc[i])
        l = float(low.iloc[i])
        v = float(vol.iloc[i])
        v_ma = float(v20.iloc[i]) if pd.notna(v20.iloc[i]) else 0
        b_up = float(bb_upper.iloc[i])
        e2 = float(e200.iloc[i])
        at = float(atr14.iloc[i]) if pd.notna(atr14.iloc[i]) else 0
        
        recent_squeeze = is_squeeze.iloc[i-3:i+1].any()
        vol_mult = v / v_ma if v_ma > 0 else 0
        
        # Apply the 2.0x - 3.0x Volume Filter
        if recent_squeeze and c > b_up and (2.0 < vol_mult < 3.0) and c > e2:
            entry = c
            sl = l
            if (entry - sl) < 0.3 * at:
                sl = entry - 0.5 * at
                
            risk = entry - sl
            if risk > 0:
                rr = 5.0
                tp = entry + rr * risk
                
                j = i + 1
                exit_idx = None
                result = None
                
                while j < len(df):
                    hi = float(high.iloc[j])
                    lo = float(low.iloc[j])
                    if lo <= sl: exit_idx, result = j, "LOSS"; break
                    if hi >= tp: exit_idx, result = j, "WIN"; break
                    j += 1
                    
                if exit_idx is not None:
                    dt = pd.to_datetime(df["timestamp"].iloc[i], utc=True)
                    dist_e200 = (c - e2) / e2 * 100
                    
                    trades.append({
                        "result": result,
                        "day_of_week": dt.dayofweek, # 0=Mon, 6=Sun
                        "hour": dt.hour,
                        "dist_e200": dist_e200
                    })
                    i = exit_idx
        i += 1
        
    wins = [t for t in trades if t["result"] == "WIN"]
    losses = [t for t in trades if t["result"] == "LOSS"]
    
    print(f"\nAnalyzed {len(trades)} trades (Wins: {len(wins)}, Losses: {len(losses)})")
    
    # 1. Day of Week Analysis
    print("\n--- DAY OF WEEK ---")
    win_days = [t['day_of_week'] for t in wins]
    loss_days = [t['day_of_week'] for t in losses]
    for d in range(7):
        w = win_days.count(d)
        l = loss_days.count(d)
        tot = w + l
        if tot > 0:
            print(f"Day {d} (0=Mon, 6=Sun): {tot} trades -> Winrate: {w/tot*100:.1f}%")
            
    # 2. Distance to EMA 200 (Over-extension)
    print("\n--- DISTANCE TO EMA 200 (Macro Over-extension) ---")
    dist_buckets = [(0, 1.0), (1.0, 3.0), (3.0, 5.0), (5.0, 15.0)]
    for low_d, high_d in dist_buckets:
        w = len([t for t in wins if low_d <= t['dist_e200'] < high_d])
        l = len([t for t in losses if low_d <= t['dist_e200'] < high_d])
        tot = w + l
        if tot > 0:
            print(f"Dist {low_d}%-{high_d}%: {tot} trades -> Winrate: {w/tot*100:.1f}%")

if __name__ == "__main__":
    analyze_eth_god()
