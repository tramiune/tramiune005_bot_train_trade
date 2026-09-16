from datetime import datetime, timedelta, timezone
import pandas as pd
import numpy as np
from server.main import _fetch_ohlcv_ccxt, _sma, _ema

def _rsi(df, period=14):
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def analyze_sol_4years():
    print("Fetching 4 years of 5m data for SOL/USDT...")
    since = datetime.now(timezone.utc) - timedelta(days=1460)
    df = _fetch_ohlcv_ccxt("binance", "SOL/USDT", "5m", since=since, limit=500000)
    
    close = df["close"].astype(float)
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    vol = df["volume"].astype(float)
    
    e800 = _ema(close, 800)
    v50 = _sma(vol, 50)
    sma20 = _sma(close, 20)
    std20 = close.rolling(20).std()
    bb_lower = sma20 - 2.5 * std20
    rsi14 = _rsi(df, 14)
    
    trades = []
    i = 805
    while i < len(df) - 1:
        c = float(close.iloc[i])
        h = float(high.iloc[i])
        l = float(low.iloc[i])
        v = float(vol.iloc[i])
        v_ma = float(v50.iloc[i]) if pd.notna(v50.iloc[i]) else 0
        b_low = float(bb_lower.iloc[i]) if pd.notna(bb_lower.iloc[i]) else 0
        e8 = float(e800.iloc[i]) if pd.notna(e800.iloc[i]) else 0
        rsi_prev = float(rsi14.iloc[i-1]) if pd.notna(rsi14.iloc[i-1]) else 50
        
        vol_mult = v / v_ma if v_ma > 0 else 0
        candle_range = h - l
        close_pct = (c - l) / candle_range if candle_range > 0 else 0
        
        if c > e8 and l < b_low and vol_mult > 4.0 and close_pct > 0.7:
            dt = pd.to_datetime(df["timestamp"].iloc[i], utc=True)
            entry = c
            sl = entry * (1 - 0.008)
            tp = entry * (1 + 0.10)
            
            j = i + 1
            result = None
            
            while j < len(df):
                hi = float(high.iloc[j])
                lo = float(low.iloc[j])
                
                if lo <= sl: 
                    result = "LOSS"
                    break
                if hi >= tp: 
                    result = "WIN"
                    break
                j += 1
                
            trades.append({
                "result": result,
                "rsi_prev": rsi_prev,
                "hour": dt.hour,
                "vol_mult": vol_mult,
                "day": dt.dayofweek
            })
            i += 10
        else:
            i += 1
            
    wins = [t for t in trades if t["result"] == "WIN"]
    losses = [t for t in trades if t["result"] == "LOSS"]
    
    print(f"\nAnalyzed {len(trades)} trades (Wins: {len(wins)}, Losses: {len(losses)})")
    
    print("\n--- RSI BEFORE SWEEP (OVERSOLD CHECK) ---")
    rsi_b = [(0, 30), (30, 40), (40, 50), (50, 100)]
    for l_r, h_r in rsi_b:
        w = len([t for t in wins if l_r <= t['rsi_prev'] < h_r])
        l = len([t for t in losses if l_r <= t['rsi_prev'] < h_r])
        tot = w + l
        if tot > 0:
            print(f"RSI {l_r}-{h_r}: {tot} trades -> Winrate: {w/tot*100:.1f}%")
            
    print("\n--- HOUR OF DAY (UTC) ---")
    asian_w = len([t for t in wins if 0 <= t['hour'] <= 8])
    asian_l = len([t for t in losses if 0 <= t['hour'] <= 8])
    asian_tot = asian_w + asian_l
    if asian_tot > 0:
        print(f"Asian (0-8 UTC): {asian_tot} trades -> Winrate: {asian_w/asian_tot*100:.1f}%")
        
    london_w = len([t for t in wins if 9 <= t['hour'] <= 13])
    london_l = len([t for t in losses if 9 <= t['hour'] <= 13])
    lon_tot = london_w + london_l
    if lon_tot > 0:
        print(f"London (9-13 UTC): {lon_tot} trades -> Winrate: {london_w/lon_tot*100:.1f}%")
        
    ny_w = len([t for t in wins if 14 <= t['hour'] <= 23])
    ny_l = len([t for t in losses if 14 <= t['hour'] <= 23])
    ny_tot = ny_w + ny_l
    if ny_tot > 0:
        print(f"NY (14-23 UTC): {ny_tot} trades -> Winrate: {ny_w/ny_tot*100:.1f}%")
        
    print("\n--- DAY OF WEEK ---")
    for d in range(7):
        w = len([t for t in wins if t['day'] == d])
        l = len([t for t in losses if t['day'] == d])
        tot = w + l
        if tot > 0:
            print(f"Day {d}: {tot} trades -> Winrate: {w/tot*100:.1f}%")

if __name__ == "__main__":
    analyze_sol_4years()
