from datetime import datetime, timedelta, timezone
import pandas as pd
import numpy as np
from server.main import _fetch_ohlcv_ccxt, _sma, _ema, _atr

def analyze_xrp():
    print("Fetching 4 years of 30m data for XRP/USDT (Mechanical)...")
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
                    candle_range = h - l
                    close_pct = (c - l) / candle_range if candle_range > 0 else 0
                    dist_e200 = (c - e2) / e2 * 100
                    
                    # Mechanical filters ONLY
                    # 1. Close in Top 50% (No huge upper wicks)
                    # 2. Distance to EMA200 < 1.0% (Breakout from base)
                    if close_pct > 0.5 and dist_e200 < 1.0:
                        trades.append({
                            "result": result,
                            "vol_mult": vol_mult
                        })
                    i = exit_idx
        i += 1
        
    wins = [t for t in trades if t["result"] == "WIN"]
    losses = [t for t in trades if t["result"] == "LOSS"]
    total = len(trades)
    wr = len(wins) / total * 100 if total else 0
    net_r = len(wins) * 10.0 - len(losses)
    
    print(f"\n--- MECHANICAL FILTER RESULTS (No Day of Week) ---")
    print(f"Total Trades: {total}")
    print(f"Wins: {len(wins)}")
    print(f"Losses: {len(losses)}")
    print(f"Winrate: {wr:.2f}%")
    print(f"Net Profit: {net_r:+.2f}R")

if __name__ == "__main__":
    analyze_xrp()
