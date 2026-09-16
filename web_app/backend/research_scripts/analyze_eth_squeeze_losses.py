from datetime import datetime, timedelta, timezone
import pandas as pd
import numpy as np
from server.main import _fetch_ohlcv_ccxt, _sma, _ema, _atr, _adx

def analyze_eth_squeeze():
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
    e50 = _ema(close, 50)
    adx14 = _adx(df, 14)
    
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
        e5 = float(e50.iloc[i])
        at = float(atr14.iloc[i]) if pd.notna(atr14.iloc[i]) else 0
        adx_val = float(adx14.iloc[i]) if pd.notna(adx14.iloc[i]) else 0
        
        recent_squeeze = is_squeeze.iloc[i-3:i+1].any()
        
        if recent_squeeze and c > b_up and v > 1.5 * v_ma and c > e2:
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
                    vol_mult = v / v_ma if v_ma > 0 else 0
                    dist_e50 = (c - e5) / e5 * 100
                    candle_range_pct = (h - l) / c * 100
                    
                    trades.append({
                        "result": result,
                        "hour": dt.hour,
                        "day_of_week": dt.dayofweek,
                        "adx": adx_val,
                        "vol_mult": vol_mult,
                        "dist_e50": dist_e50,
                        "candle_range_pct": candle_range_pct
                    })
                    i = exit_idx
        i += 1
        
    wins = [t for t in trades if t["result"] == "WIN"]
    losses = [t for t in trades if t["result"] == "LOSS"]
    
    print(f"\nAnalyzed {len(trades)} trades (Wins: {len(wins)}, Losses: {len(losses)})")
    
    # Analyze ADX (Trend Strength before breakout)
    print("\n--- ADX BUCKETS (Trend Strength) ---")
    adx_buckets = [(0, 20), (20, 25), (25, 100)]
    for low_a, high_a in adx_buckets:
        w = len([t for t in wins if low_a <= t['adx'] < high_a])
        l = len([t for t in losses if low_a <= t['adx'] < high_a])
        tot = w + l
        if tot > 0:
            print(f"ADX {low_a}-{high_a}: {tot} trades -> Winrate: {w/tot*100:.1f}%")
            
    # Analyze Volume Multiplier
    print("\n--- VOLUME MULTIPLIER BUCKETS ---")
    vol_buckets = [(1.5, 2.0), (2.0, 3.0), (3.0, 10.0)]
    for low_v, high_v in vol_buckets:
        w = len([t for t in wins if low_v <= t['vol_mult'] < high_v])
        l = len([t for t in losses if low_v <= t['vol_mult'] < high_v])
        tot = w + l
        if tot > 0:
            print(f"Vol {low_v}x-{high_v}x: {tot} trades -> Winrate: {w/tot*100:.1f}%")

    # Analyze Session
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
    analyze_eth_squeeze()
