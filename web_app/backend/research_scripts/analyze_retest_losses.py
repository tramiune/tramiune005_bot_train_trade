from datetime import datetime, timedelta, timezone
import pandas as pd
import numpy as np
from server.main import _fetch_ohlcv_ccxt, _sma, _ema, _atr

def analyze_losses():
    print("Fetching 4 years of 1h data for SOL/USDT...")
    since = datetime.now(timezone.utc) - timedelta(days=1460)
    df = _fetch_ohlcv_ccxt("binance", "SOL/USDT", "1h", since=since, limit=100000)
    
    close = df["close"].astype(float)
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    vol = df["volume"].astype(float)
    
    e200 = _ema(close, 200)
    e800 = _ema(close, 800)
    e20 = _ema(close, 20)
    atr14 = _atr(df, 14)
    v20 = _sma(vol, 20)
    
    trades = []
    i = 805
    last_bullish_cross_idx = 0
    rr_target = 3.0
    
    while i < len(df) - 1:
        c = float(close.iloc[i])
        h = float(high.iloc[i])
        l = float(low.iloc[i])
        v = float(vol.iloc[i])
        
        e200_val = float(e200.iloc[i]) if pd.notna(e200.iloc[i]) else 0
        e800_val = float(e800.iloc[i]) if pd.notna(e800.iloc[i]) else 0
        e20_val = float(e20.iloc[i]) if pd.notna(e20.iloc[i]) else 0
        prev_e20 = float(e20.iloc[i-1]) if pd.notna(e20.iloc[i-1]) else 0
        prev_e200 = float(e200.iloc[i-1]) if pd.notna(e200.iloc[i-1]) else 0
        at = float(atr14.iloc[i]) if pd.notna(atr14.iloc[i]) else 0
        v_ma = float(v20.iloc[i]) if pd.notna(v20.iloc[i]) else 0
        
        if prev_e20 <= prev_e200 and e20_val > e200_val:
            last_bullish_cross_idx = i
            
        candle_range = h - l
        close_pct = (c - l) / candle_range if candle_range > 0 else 0
        
        is_uptrend = e20_val > e200_val
        candles_since_cross = i - last_bullish_cross_idx
        is_fresh_trend = candles_since_cross < 150
        is_touching = l <= e200_val and c > e200_val
        is_rejection = close_pct > 0.5
        
        if is_uptrend and is_fresh_trend and is_touching and is_rejection:
            entry = c
            sl = entry - 1.5 * at
            
            risk = entry - sl
            if risk > 0:
                tp = entry + rr_target * risk
                
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
                    # Gather features for analysis
                    vol_mult = v / v_ma if v_ma > 0 else 0
                    is_macro_bull = c > e800_val
                    
                    trades.append({
                        "result": result,
                        "close_pct": close_pct,
                        "vol_mult": vol_mult,
                        "macro_bull": is_macro_bull,
                        "time_since_cross": candles_since_cross
                    })
                    
                    i = exit_idx
                    continue
        i += 1
        
    wins = [t for t in trades if t["result"] == "WIN"]
    losses = [t for t in trades if t["result"] == "LOSS"]
    
    print(f"\nAnalyzed {len(trades)} trades (Wins: {len(wins)}, Losses: {len(losses)})")
    
    print("\n--- 1. MACRO TREND FILTER (Close > EMA 800) ---")
    w = len([t for t in wins if t["macro_bull"]])
    l = len([t for t in losses if t["macro_bull"]])
    tot = w + l
    print(f"In Macro Bull (C > E800): {tot} trades -> WR: {w/tot*100:.1f}%" if tot else "None")
    
    w = len([t for t in wins if not t["macro_bull"]])
    l = len([t for t in losses if not t["macro_bull"]])
    tot = w + l
    print(f"In Macro Bear (C < E800): {tot} trades -> WR: {w/tot*100:.1f}%" if tot else "None")
    
    print("\n--- 2. SPEED OF RETEST (Candles since Cross) ---")
    for r in [(0, 20), (20, 50), (50, 100), (100, 150)]:
        w = len([t for t in wins if r[0] <= t["time_since_cross"] < r[1]])
        l = len([t for t in losses if r[0] <= t["time_since_cross"] < r[1]])
        tot = w + l
        if tot > 0: print(f"{r[0]:>3}-{r[1]:>3} candles: {tot:>3} trades -> WR: {w/tot*100:.1f}%")
        
    print("\n--- 3. REJECTION STRENGTH (Close % in Candle) ---")
    for r in [(0.5, 0.6), (0.6, 0.8), (0.8, 1.0)]:
        w = len([t for t in wins if r[0] <= t["close_pct"] < r[1]])
        l = len([t for t in losses if r[0] <= t["close_pct"] < r[1]])
        tot = w + l
        if tot > 0: print(f"Close Top {100-r[1]*100:.0f}%-{100-r[0]*100:.0f}%: {tot:>3} trades -> WR: {w/tot*100:.1f}%")
        
    print("\n--- 4. RETEST VOLUME (Vol / MA) ---")
    for r in [(0, 1.0), (1.0, 1.5), (1.5, 5.0)]:
        w = len([t for t in wins if r[0] <= t["vol_mult"] < r[1]])
        l = len([t for t in losses if r[0] <= t["vol_mult"] < r[1]])
        tot = w + l
        if tot > 0: print(f"Vol {r[0]:.1f}x-{r[1]:.1f}x: {tot:>3} trades -> WR: {w/tot*100:.1f}%")

if __name__ == "__main__":
    analyze_losses()
