from datetime import datetime, timedelta, timezone
import pandas as pd
import numpy as np
from server.main import _fetch_ohlcv_ccxt, _sma, _ema, _atr

def analyze_xrp():
    print("Fetching 4 years of 30m data for XRP/USDT...")
    since = datetime.now(timezone.utc) - timedelta(days=1460)
    df = _fetch_ohlcv_ccxt("binance", "XRP/USDT", "30m", since=since, limit=100000)
    
    close = df["close"].astype(float)
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    vol = df["volume"].astype(float)
    
    sma20 = _sma(close, 20)
    std20 = close.rolling(20).std()
    bb_upper = sma20 + 2 * std20
    bb_lower = sma20 - 2 * std20
    bbw = (bb_upper - bb_lower) / sma20 * 100
    
    atr14 = _atr(df, 14)
    v20 = _sma(vol, 20)
    e200 = _ema(close, 200)
    
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
        
        bbw_sleep = False
        if i >= 5:
            recent_bbw = bbw.iloc[i-5:i]
            if not recent_bbw.isna().any() and recent_bbw.min() < 1.2:
                bbw_sleep = True
                
        vol_mult = v / v_ma if v_ma > 0 else 0
        
        if bbw_sleep and c > b_up and vol_mult > 3.0 and c > e2:
            entry = c
            sl = l
            if (entry - sl) < 0.3 * at:
                sl = entry - 0.5 * at
                
            risk = entry - sl
            if risk > 0:
                rr = 10.0
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
                    candle_range = h - l
                    close_pct = (c - l) / candle_range if candle_range > 0 else 0
                    dist_e200 = (c - e2) / e2 * 100
                    
                    trades.append({
                        "result": result,
                        "vol_mult": vol_mult,
                        "hour": dt.hour,
                        "day_of_week": dt.dayofweek,
                        "close_pct": close_pct,
                        "dist_e200": dist_e200,
                        "candle_size": candle_range / c * 100
                    })
                    i = exit_idx
        i += 1
        
    wins = [t for t in trades if t["result"] == "WIN"]
    losses = [t for t in trades if t["result"] == "LOSS"]
    
    print(f"\nAnalyzed {len(trades)} trades (Wins: {len(wins)}, Losses: {len(losses)})")
    
    print("\n--- VOLUME MULTIPLIER ---")
    vol_buckets = [(3.0, 4.0), (4.0, 6.0), (6.0, 10.0), (10.0, 100.0)]
    for l_v, h_v in vol_buckets:
        w = len([t for t in wins if l_v <= t['vol_mult'] < h_v])
        l = len([t for t in losses if l_v <= t['vol_mult'] < h_v])
        tot = w + l
        if tot > 0:
            print(f"Vol {l_v}x - {h_v}x: {tot} trades -> Winrate: {w/tot*100:.1f}%")
            
    print("\n--- CANDLE CLOSE PERCENT ---")
    close_buckets = [(0.0, 0.5), (0.5, 0.7), (0.7, 0.9), (0.9, 1.0)]
    for l_c, h_c in close_buckets:
        w = len([t for t in wins if l_c <= t['close_pct'] < h_c])
        l = len([t for t in losses if l_c <= t['close_pct'] < h_c])
        tot = w + l
        if tot > 0:
            print(f"Top {100-h_c*100:.0f}%-{100-l_c*100:.0f}%: {tot} trades -> Winrate: {w/tot*100:.1f}%")

    print("\n--- DAY OF WEEK ---")
    for d in range(7):
        w = len([t for t in wins if t['day_of_week'] == d])
        l = len([t for t in losses if t['day_of_week'] == d])
        tot = w + l
        if tot > 0:
            print(f"Day {d}: {tot} trades -> Winrate: {w/tot*100:.1f}%")

    print("\n--- DISTANCE TO EMA 200 ---")
    dist_b = [(0.0, 1.0), (1.0, 2.0), (2.0, 5.0), (5.0, 20.0)]
    for l_d, h_d in dist_b:
        w = len([t for t in wins if l_d <= t['dist_e200'] < h_d])
        l = len([t for t in losses if l_d <= t['dist_e200'] < h_d])
        tot = w + l
        if tot > 0:
            print(f"Dist {l_d}%-{h_d}%: {tot} trades -> Winrate: {w/tot*100:.1f}%")

if __name__ == "__main__":
    analyze_xrp()
