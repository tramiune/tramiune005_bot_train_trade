from datetime import datetime, timedelta, timezone
import pandas as pd
import numpy as np
from server.main import _fetch_ohlcv_ccxt, _sma, _ema

def test_smc_8years():
    print("Fetching 8 years (2920 days) of 1h data for Ultimate Stress Test...")
    since = datetime.now(timezone.utc) - timedelta(days=2920)
    df = _fetch_ohlcv_ccxt("binance", "BTC/USDT", "1h", since=since, limit=100000)
    
    print(f"Loaded {len(df)} 1h candles.")
    
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
        dt = pd.to_datetime(df["timestamp"].iloc[i], utc=True)
        
        # Bullish context + Volume boundaries + No Mondays
        if c > e2 and l < lb and (1.5 * v_ma < v < 2.0 * v_ma) and dt.dayofweek != 0:
            candle_range = h - l
            if candle_range > 0:
                close_percent = (c - l) / candle_range
                
                # Check Crash Intensity (5-hour drop)
                prev_5_drop = (float(close.iloc[i-5]) - c) / c * 100
                
                # Check Over-extension (Distance to EMA 200)
                dist_to_e200 = (c - e2) / e2 * 100
                
                # Rejection AND NOT falling knife AND NOT over-extended
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
                            trades.append({"result": result})
                            i = exit_idx
        i += 1
        
    wins = [t for t in trades if t["result"] == "WIN"]
    losses = [t for t in trades if t["result"] == "LOSS"]
    total = len(trades)
    wr = len(wins) / total * 100 if total else 0
    
    print("\n--- 8-YEAR ULTIMATE SMART MONEY BACKTEST (2018 - 2026) ---")
    print(f"Total Trades: {total}")
    print(f"Wins: {len(wins)}")
    print(f"Losses: {len(losses)}")
    print(f"Winrate: {wr:.2f}% (RR = 2.0)")
    
    if total > 0:
        net_r = len(wins) * 2 - len(losses)
        print(f"Net Profit: {net_r:+.2f}R")

if __name__ == "__main__":
    test_smc_8years()
