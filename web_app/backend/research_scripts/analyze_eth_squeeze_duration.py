from datetime import datetime, timedelta, timezone
import pandas as pd
import numpy as np
from server.main import _fetch_ohlcv_ccxt, _sma, _ema, _atr

def analyze_duration():
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
    
    # Calculate Squeeze Duration
    squeeze_durations = []
    current_duration = 0
    for val in is_squeeze:
        if val:
            current_duration += 1
        else:
            current_duration = 0
        squeeze_durations.append(current_duration)
    
    df['squeeze_duration'] = squeeze_durations
    
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
        dt = pd.to_datetime(df["timestamp"].iloc[i], utc=True)
        
        recent_squeeze = is_squeeze.iloc[i-3:i+1].any()
        max_duration = df['squeeze_duration'].iloc[i-10:i+1].max()
        vol_mult = v / v_ma if v_ma > 0 else 0
        dist_e200 = (c - e2) / e2 * 100
        
        # Base filters
        if recent_squeeze and c > b_up and (2.0 < vol_mult < 3.0) and c > e2 and dt.dayofweek != 0 and dist_e200 >= 1.0:
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
                    trades.append({
                        "result": result,
                        "duration": max_duration
                    })
                    i = exit_idx
        i += 1
        
    wins = [t for t in trades if t["result"] == "WIN"]
    losses = [t for t in trades if t["result"] == "LOSS"]
    
    print(f"\nAnalyzed {len(trades)} highly filtered trades (Wins: {len(wins)}, Losses: {len(losses)})")
    wr = len(wins) / len(trades) * 100 if trades else 0
    print(f"Current Winrate: {wr:.2f}%")
    
    print("\n--- SQUEEZE DURATION BUCKETS ---")
    buckets = [(0, 3), (3, 6), (6, 12), (12, 100)]
    for low_d, high_d in buckets:
        w = len([t for t in wins if low_d <= t['duration'] < high_d])
        l = len([t for t in losses if low_d <= t['duration'] < high_d])
        tot = w + l
        if tot > 0:
            print(f"Duration {low_d}h - {high_d}h: {tot} trades -> Winrate: {w/tot*100:.1f}%")

if __name__ == "__main__":
    analyze_duration()
