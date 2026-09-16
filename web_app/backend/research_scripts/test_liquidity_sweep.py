from datetime import datetime, timedelta, timezone
import pandas as pd
import numpy as np
from server.main import _fetch_ohlcv_ccxt, _sma, _rolling_low, _ema

def test_sweep():
    print("Fetching 180 days of 1h data...")
    since = datetime.now(timezone.utc) - timedelta(days=180)
    df = _fetch_ohlcv_ccxt("binance", "BTC/USDT", "1h", since=since, limit=50000)
    
    close = df["close"].astype(float)
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    vol = df["volume"].astype(float)
    
    e200 = _ema(close, 200)
    v20 = _sma(vol, 20)
    
    lowest_20 = _rolling_low(low, 20).shift(1)
    
    trades = []
    i = 205
    while i < len(df) - 1:
        c = float(close.iloc[i])
        h = float(high.iloc[i])
        l = float(low.iloc[i])
        v = float(vol.iloc[i])
        v_ma = float(v20.iloc[i])
        e2 = float(e200.iloc[i])
        prev_low = float(lowest_20.iloc[i])
        
        # Uptrend
        if c > e2:
            # Sweep condition: pierce the previous support but close above it
            if l < prev_low and c > prev_low:
                # Volume confirmation (smart money bought the dip)
                if v > v_ma * 1.2:
                    entry = c
                    sl = l - (h - l) * 0.1 # Just below the sweep low
                    risk = entry - sl
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
                        if exit_idx:
                            trades.append(result)
                            i = exit_idx
        i += 1
        
    wins = trades.count("WIN")
    total = len(trades)
    wr = wins / total * 100 if total else 0
    print(f"Total: {total} | Wins: {wins} | WR: {wr:.2f}% (RR = 2.0)")

if __name__ == "__main__":
    test_sweep()
