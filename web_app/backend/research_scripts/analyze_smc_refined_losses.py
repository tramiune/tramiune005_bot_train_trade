from datetime import datetime, timedelta, timezone
import pandas as pd
import numpy as np
from server.main import _fetch_ohlcv_ccxt, _sma, _ema, _adx

def analyze_smc_refined():
    print("Fetching 4 years of 1h data...")
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
    adx = _adx(df, 14)

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
        a = float(adx.iloc[i]) if pd.notna(adx.iloc[i]) else 0
        
        if c > e2 and l < lb and v > 1.5 * v_ma:
            candle_range = h - l
            if candle_range > 0:
                close_percent = (c - l) / candle_range
                prev_5_drop = (float(close.iloc[i-5]) - c) / c * 100
                
                if close_percent > 0.5 and prev_5_drop < 0.6:
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
                            entry_time = pd.to_datetime(df["timestamp"].iloc[i], utc=True)
                            dist_to_e200 = (c - e2) / e2 * 100
                            vol_mult = v / v_ma if v_ma > 0 else 0
                            
                            trades.append({
                                "time": entry_time,
                                "result": result,
                                "hour": entry_time.hour,
                                "adx": a,
                                "dist_to_e200": dist_to_e200,
                                "vol_mult": vol_mult,
                                "candle_range_pct": candle_range / c * 100
                            })
                            i = exit_idx
        i += 1
        
    wins = [t for t in trades if t["result"] == "WIN"]
    losses = [t for t in trades if t["result"] == "LOSS"]
    
    print(f"\nAnalyzing remaining 78 losses vs 47 wins...")
    
    # Analyze Time of Day
    win_hours = [t['hour'] for t in wins]
    loss_hours = [t['hour'] for t in losses]
    
    print("\n[Hour of Day]")
    print(f"Wins happen most in hours: {pd.Series(win_hours).mode().tolist()}")
    print(f"Losses happen most in hours: {pd.Series(loss_hours).mode().tolist()}")
    
    # Analyze Averages
    def avg(lst, key):
        return sum(t[key] for t in lst) / len(lst) if lst else 0
        
    print("\n[Metrics (Wins vs Losses)]")
    print(f"ADX (Trend Strength):    W={avg(wins, 'adx'):.2f} | L={avg(losses, 'adx'):.2f}")
    print(f"Dist to EMA200 (%):      W={avg(wins, 'dist_to_e200'):.2f}% | L={avg(losses, 'dist_to_e200'):.2f}%")
    print(f"Volume Multiplier:       W={avg(wins, 'vol_mult'):.2f}x | L={avg(losses, 'vol_mult'):.2f}x")
    print(f"Candle Size (Volatility):W={avg(wins, 'candle_range_pct'):.2f}% | L={avg(losses, 'candle_range_pct'):.2f}%")

if __name__ == "__main__":
    analyze_smc_refined()
