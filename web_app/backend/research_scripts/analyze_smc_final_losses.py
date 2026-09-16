from datetime import datetime, timedelta, timezone
import pandas as pd
import numpy as np
from server.main import _fetch_ohlcv_ccxt, _sma, _ema

def analyze_smc_final():
    print("Fetching 4 years of 1h data for Deep Analysis...")
    since = datetime.now(timezone.utc) - timedelta(days=1460)
    df = _fetch_ohlcv_ccxt("binance", "BTC/USDT", "1h", since=since, limit=50000)
    
    close = df["close"].astype(float)
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    vol = df["volume"].astype(float)
    
    e200 = _ema(close, 200)
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
        lb = float(lower_band.iloc[i]) if pd.notna(lower_band.iloc[i]) else 0
        
        if c > e2 and l < lb and v > 1.5 * v_ma:
            candle_range = h - l
            if candle_range > 0:
                close_percent = (c - l) / candle_range
                prev_5_drop = (float(close.iloc[i-5]) - c) / c * 100
                dist_to_e200 = (c - e2) / e2 * 100
                
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
                            dt = pd.to_datetime(df["timestamp"].iloc[i], utc=True)
                            vol_mult = v / v_ma if v_ma > 0 else 0
                            
                            trades.append({
                                "time": dt,
                                "result": result,
                                "day_of_week": dt.dayofweek, # 0=Mon, 6=Sun
                                "hour": dt.hour,
                                "vol_mult": vol_mult,
                                "candle_size_pct": candle_range / c * 100,
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
            
    # 2. Volume Multiplier limits
    print("\n--- VOLUME MULTIPLIER ---")
    avg_v_win = sum(t['vol_mult'] for t in wins) / len(wins) if wins else 0
    avg_v_loss = sum(t['vol_mult'] for t in losses) / len(losses) if losses else 0
    print(f"Avg Vol Multiplier: Wins={avg_v_win:.2f}x | Losses={avg_v_loss:.2f}x")
    
    # 3. Time of Day (Sessions)
    print("\n--- HOUR OF DAY ---")
    asian_session_w = len([t for t in wins if 0 <= t['hour'] <= 8])
    asian_session_l = len([t for t in losses if 0 <= t['hour'] <= 8])
    asian_tot = asian_session_w + asian_session_l
    if asian_tot > 0:
        print(f"Asian Session (00:00 - 08:00 UTC): Winrate = {asian_session_w/asian_tot*100:.1f}% ({asian_tot} trades)")
        
    ny_session_w = len([t for t in wins if 12 <= t['hour'] <= 20])
    ny_session_l = len([t for t in losses if 12 <= t['hour'] <= 20])
    ny_tot = ny_session_w + ny_session_l
    if ny_tot > 0:
        print(f"NY Session (12:00 - 20:00 UTC): Winrate = {ny_session_w/ny_tot*100:.1f}% ({ny_tot} trades)")

if __name__ == "__main__":
    analyze_smc_final()
