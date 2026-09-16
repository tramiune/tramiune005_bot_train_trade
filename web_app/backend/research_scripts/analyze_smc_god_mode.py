from datetime import datetime, timedelta, timezone
import pandas as pd
import numpy as np
from server.main import _fetch_ohlcv_ccxt, _sma, _ema

def analyze_smc_god():
    print("Fetching 4 years of 1h data...")
    since = datetime.now(timezone.utc) - timedelta(days=1460)
    df = _fetch_ohlcv_ccxt("binance", "BTC/USDT", "1h", since=since, limit=50000)
    
    close = df["close"].astype(float)
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    vol = df["volume"].astype(float)
    
    e200 = _ema(close, 200)
    e50 = _ema(close, 50)
    v20 = _sma(vol, 20)
    sma20 = _sma(close, 20)
    std20 = close.rolling(20).std()
    lower_band = sma20 - 2 * std20
    
    trades = []
    i = 205
    
    while i < len(df) - 1:
        c = float(close.iloc[i])
        h = float(high.iloc[i])
        l = float(low.iloc[i])
        v = float(vol.iloc[i])
        v_ma = float(v20.iloc[i]) if pd.notna(v20.iloc[i]) else 0
        e2 = float(e200.iloc[i])
        e5 = float(e50.iloc[i])
        lb = float(lower_band.iloc[i]) if pd.notna(lower_band.iloc[i]) else 0
        dt = pd.to_datetime(df["timestamp"].iloc[i], utc=True)
        
        # Exclude Mondays (day_of_week == 0)
        if c > e2 and l < lb and v > 1.5 * v_ma and dt.dayofweek != 0:
            candle_range = h - l
            if candle_range > 0:
                close_percent = (c - l) / candle_range
                prev_5_drop = (float(close.iloc[i-5]) - c) / c * 100
                dist_to_e200 = (c - e2) / e2 * 100
                dist_to_e50 = (c - e5) / e5 * 100
                
                if close_percent > 0.5 and prev_5_drop < 0.6 and dist_to_e200 < 2.0:
                    entry = c
                    sl = l - (candle_range * 0.2)
                    risk = abs(entry - sl)
                    if risk > 0:
                        rr = 2.0
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
                            vol_mult = v / v_ma if v_ma > 0 else 0
                            
                            trades.append({
                                "result": result,
                                "hour": dt.hour,
                                "vol_mult": vol_mult,
                                "dist_e50": dist_to_e50
                            })
                            i = exit_idx
        i += 1
        
    wins = [t for t in trades if t["result"] == "WIN"]
    losses = [t for t in trades if t["result"] == "LOSS"]
    
    print(f"\nAnalyzed {len(trades)} trades (Wins: {len(wins)}, Losses: {len(losses)})")
    
    # 1. Volume Multiplier Buckets
    print("\n--- VOLUME MULTIPLIER BUCKETS ---")
    buckets = [(1.5, 2.0), (2.0, 3.0), (3.0, 10.0)]
    for low, high_v in buckets:
        w = len([t for t in wins if low <= t['vol_mult'] < high_v])
        l = len([t for t in losses if low <= t['vol_mult'] < high_v])
        tot = w + l
        if tot > 0:
            print(f"Vol {low}x - {high_v}x: {tot} trades -> Winrate: {w/tot*100:.1f}%")

    # 2. Distance to EMA 50 (Short-term trend)
    print("\n--- DISTANCE TO EMA 50 (Local Trend) ---")
    buckets_e50 = [(-5.0, -1.0), (-1.0, 0.0), (0.0, 1.0), (1.0, 5.0)]
    for low, high_v in buckets_e50:
        w = len([t for t in wins if low <= t['dist_e50'] < high_v])
        l = len([t for t in losses if low <= t['dist_e50'] < high_v])
        tot = w + l
        if tot > 0:
            print(f"Dist to EMA50 {low}% to {high_v}%: {tot} trades -> Winrate: {w/tot*100:.1f}%")
            
    # 3. Session Hours
    print("\n--- SESSION HOURS ---")
    asian_w = len([t for t in wins if 0 <= t['hour'] <= 8])
    asian_l = len([t for t in losses if 0 <= t['hour'] <= 8])
    asian_tot = asian_w + asian_l
    if asian_tot > 0:
        print(f"Asian Session (0-8 UTC): {asian_tot} trades -> Winrate: {asian_w/asian_tot*100:.1f}%")
        
    eu_ny_w = len([t for t in wins if 12 <= t['hour'] <= 22])
    eu_ny_l = len([t for t in losses if 12 <= t['hour'] <= 22])
    eu_ny_tot = eu_ny_w + eu_ny_l
    if eu_ny_tot > 0:
        print(f"EU/NY Session (12-22 UTC): {eu_ny_tot} trades -> Winrate: {eu_ny_w/eu_ny_tot*100:.1f}%")

if __name__ == "__main__":
    analyze_smc_god()
