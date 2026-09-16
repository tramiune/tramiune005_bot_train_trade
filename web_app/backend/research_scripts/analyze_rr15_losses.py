from datetime import datetime, timedelta, timezone
import pandas as pd
import numpy as np
from server.main import _fetch_ohlcv_ccxt, _sma, _ema, _atr

def run_analysis():
    print("Fetching 4 years of 1h data for SOL and BTC...")
    since = datetime.now(timezone.utc) - timedelta(days=1460)
    
    # Fetch SOL
    sol = _fetch_ohlcv_ccxt("binance", "SOL/USDT", "1h", since=since, limit=100000)
    
    # Fetch BTC for Macro filter
    btc = _fetch_ohlcv_ccxt("binance", "BTC/USDT", "1h", since=since, limit=100000)
    
    # Ensure they align by timestamp (using merge)
    btc = btc[["timestamp", "close"]].rename(columns={"close": "btc_close"})
    df = pd.merge(sol, btc, on="timestamp", how="left")
    
    # Calculate indicators
    df["e200"] = _ema(df["close"], 200)
    df["e20"] = _ema(df["close"], 20)
    df["atr14"] = _atr(df, 14)
    df["v20"] = _sma(df["volume"], 20)
    
    df["btc_e200"] = _ema(df["btc_close"], 200)
    
    trades = []
    i = 205
    last_bullish_cross_idx = 0
    rr_target = 15.0
    
    while i < len(df) - 1:
        c = float(df["close"].iloc[i])
        h = float(df["high"].iloc[i])
        l = float(df["low"].iloc[i])
        v = float(df["volume"].iloc[i])
        
        e200_val = float(df["e200"].iloc[i]) if pd.notna(df["e200"].iloc[i]) else 0
        e20_val = float(df["e20"].iloc[i]) if pd.notna(df["e20"].iloc[i]) else 0
        prev_e20 = float(df["e20"].iloc[i-1]) if pd.notna(df["e20"].iloc[i-1]) else 0
        prev_e200 = float(df["e200"].iloc[i-1]) if pd.notna(df["e200"].iloc[i-1]) else 0
        at = float(df["atr14"].iloc[i]) if pd.notna(df["atr14"].iloc[i]) else 0
        v_ma = float(df["v20"].iloc[i]) if pd.notna(df["v20"].iloc[i]) else 0
        
        btc_c = float(df["btc_close"].iloc[i]) if pd.notna(df["btc_close"].iloc[i]) else 0
        btc_e200_val = float(df["btc_e200"].iloc[i]) if pd.notna(df["btc_e200"].iloc[i]) else 0
        
        if prev_e20 <= prev_e200 and e20_val > e200_val:
            last_bullish_cross_idx = i
            
        candle_range = h - l
        close_pct = (c - l) / candle_range if candle_range > 0 else 0
        
        is_uptrend = e20_val > e200_val
        candles_since_cross = i - last_bullish_cross_idx
        is_proper_speed = 20 <= candles_since_cross < 150
        is_strong_rejection = close_pct > 0.6
        has_volume = (v / v_ma) > 1.2 if v_ma > 0 else False
        is_touching = l <= e200_val and c > e200_val
        
        if is_uptrend and is_proper_speed and is_touching and is_strong_rejection and has_volume:
            entry = c
            sl = entry - 1.5 * at
            
            risk = entry - sl
            if risk > 0:
                tp = entry + rr_target * risk
                
                j = i + 1
                exit_idx = None
                result = None
                
                while j < len(df):
                    hi = float(df["high"].iloc[j])
                    lo = float(df["low"].iloc[j])
                    if lo <= sl: exit_idx, result = j, "LOSS"; break
                    if hi >= tp: exit_idx, result = j, "WIN"; break
                    j += 1
                    
                if exit_idx is not None:
                    trades.append({
                        "result": result,
                        "btc_bullish": btc_c > btc_e200_val,
                        "vol_mult": v / v_ma
                    })
                    i = exit_idx
                    continue
        i += 1
        
    wins = [t for t in trades if t["result"] == "WIN"]
    losses = [t for t in trades if t["result"] == "LOSS"]
    
    print(f"\nAnalyzed {len(trades)} trades for RR 15.0 (Wins: {len(wins)}, Losses: {len(losses)})")
    
    print("\n--- 1. BITCOIN MACRO FILTER (BTC > EMA 200) ---")
    w = len([t for t in wins if t["btc_bullish"]])
    l = len([t for t in losses if t["btc_bullish"]])
    tot = w + l
    if tot > 0: print(f"BTC Bullish: {tot:>2} trades -> Wins: {w}, Losses: {l} (WR: {w/tot*100:.1f}%) -> Net Profit: {(w*15)-l:+.1f}R")
    
    w = len([t for t in wins if not t["btc_bullish"]])
    l = len([t for t in losses if not t["btc_bullish"]])
    tot = w + l
    if tot > 0: print(f"BTC Bearish: {tot:>2} trades -> Wins: {w}, Losses: {l} (WR: {w/tot*100:.1f}%) -> Net Profit: {(w*15)-l:+.1f}R")
    
    print("\n--- 2. EXTREME VOLUME FILTER (Vol > 2.0x) ---")
    w = len([t for t in wins if t["vol_mult"] > 2.0])
    l = len([t for t in losses if t["vol_mult"] > 2.0])
    tot = w + l
    if tot > 0: print(f"Vol > 2.0x: {tot:>2} trades -> Wins: {w}, Losses: {l} (WR: {w/tot*100:.1f}%) -> Net Profit: {(w*15)-l:+.1f}R")

if __name__ == "__main__":
    run_analysis()
