from datetime import datetime, timedelta, timezone
import pandas as pd
import numpy as np
from server.main import _fetch_ohlcv_ccxt, _sma, _ema

def _rsi(s, n=14):
    delta = s.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=n).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=n).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def analyze_smc():
    print("Fetching data for SMC loss analysis...")
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
    
    rsi = _rsi(close, 14)

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
                if close_percent > 0.5:
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
                            # Context for analysis
                            r_val = float(rsi.iloc[i])
                            dist_to_e50 = (float(e50.iloc[i]) - c) / c * 100
                            # Look back 5 candles for momentum
                            prev_5_drop = (float(close.iloc[i-5]) - c) / c * 100
                            
                            trades.append({
                                "entry_time": df["timestamp"].iloc[i],
                                "entry": entry,
                                "result": result,
                                "rsi": r_val,
                                "dist_to_e50": dist_to_e50,
                                "prev_5_drop": prev_5_drop
                            })
                            i = exit_idx
        i += 1
        
    losses = [t for t in trades if t["result"] == "LOSS"]
    wins = [t for t in trades if t["result"] == "WIN"]
    
    print(f"\nAnalyzed {len(trades)} trades (Wins: {len(wins)}, Losses: {len(losses)})")
    
    print("\n--- ANALYSIS OF LOSING TRADES (Why did they fail?) ---")
    for t in losses[-5:]:
        print(f"[{t['entry_time']}] Loss at {t['entry']:.2f}")
        print(f"   -> RSI at entry: {t['rsi']:.2f}")
        print(f"   -> Distance below EMA50: {t['dist_to_e50']:.2f}%")
        print(f"   -> 5-hr crash intensity: {t['prev_5_drop']:.2f}% drop")
        print("-" * 40)
        
    # Analyze averages
    avg_rsi_loss = sum(t['rsi'] for t in losses) / len(losses) if losses else 0
    avg_rsi_win = sum(t['rsi'] for t in wins) / len(wins) if wins else 0
    print(f"Avg RSI on Losses: {avg_rsi_loss:.2f} | Avg RSI on Wins: {avg_rsi_win:.2f}")
    
    avg_drop_loss = sum(t['prev_5_drop'] for t in losses) / len(losses) if losses else 0
    avg_drop_win = sum(t['prev_5_drop'] for t in wins) / len(wins) if wins else 0
    print(f"Avg 5h Drop on Losses: {avg_drop_loss:.2f}% | Avg 5h Drop on Wins: {avg_drop_win:.2f}%")

if __name__ == "__main__":
    analyze_smc()
