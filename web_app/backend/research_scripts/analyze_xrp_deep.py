from datetime import datetime, timedelta, timezone
import pandas as pd
import numpy as np
from server.main import _fetch_ohlcv_ccxt, _sma, _ema, _atr

def _rsi(df, period=14):
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def analyze_xrp():
    print("Fetching 4 years of 30m data for XRP/USDT (Deep)...")
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
    rsi14 = _rsi(df, 14)
    
    bbw_sleep_series = bbw < 1.2
    squeeze_durations = []
    current_duration = 0
    for val in bbw_sleep_series:
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
                    max_duration = df['squeeze_duration'].iloc[i-10:i+1].max()
                    rsi_prev = float(rsi14.iloc[i-1]) if pd.notna(rsi14.iloc[i-1]) else 50
                    candle_size = (h - l) / c * 100
                    
                    trades.append({
                        "result": result,
                        "duration": max_duration,
                        "rsi_prev": rsi_prev,
                        "candle_size": candle_size
                    })
                    i = exit_idx
        i += 1
        
    wins = [t for t in trades if t["result"] == "WIN"]
    losses = [t for t in trades if t["result"] == "LOSS"]
    
    print(f"\nAnalyzed {len(trades)} trades (Wins: {len(wins)}, Losses: {len(losses)})")
    
    print("\n--- SQUEEZE DURATION ---")
    dur_b = [(0, 5), (5, 10), (10, 20), (20, 100)]
    for l_d, h_d in dur_b:
        w = len([t for t in wins if l_d <= t['duration'] < h_d])
        l = len([t for t in losses if l_d <= t['duration'] < h_d])
        tot = w + l
        if tot > 0:
            print(f"Dur {l_d}-{h_d} candles: {tot} trades -> Winrate: {w/tot*100:.1f}%")

    print("\n--- RSI BEFORE BREAKOUT ---")
    rsi_b = [(0, 50), (50, 60), (60, 70), (70, 100)]
    for l_r, h_r in rsi_b:
        w = len([t for t in wins if l_r <= t['rsi_prev'] < h_r])
        l = len([t for t in losses if l_r <= t['rsi_prev'] < h_r])
        tot = w + l
        if tot > 0:
            print(f"RSI {l_r}-{h_r}: {tot} trades -> Winrate: {w/tot*100:.1f}%")
            
    print("\n--- CANDLE SIZE (% of price) ---")
    size_b = [(0.0, 0.5), (0.5, 1.0), (1.0, 2.0), (2.0, 10.0)]
    for l_s, h_s in size_b:
        w = len([t for t in wins if l_s <= t['candle_size'] < h_s])
        l = len([t for t in losses if l_s <= t['candle_size'] < h_s])
        tot = w + l
        if tot > 0:
            print(f"Size {l_s}%-{h_s}%: {tot} trades -> Winrate: {w/tot*100:.1f}%")

if __name__ == "__main__":
    analyze_xrp()
