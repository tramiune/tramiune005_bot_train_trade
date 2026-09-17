from datetime import datetime, timedelta, timezone
import pandas as pd
import numpy as np
from server.main import _fetch_ohlcv_ccxt, _sma, _ema, _atr, _adx

def run_analysis():
    print("Fetching 4 years of 1h and 1d data for SOL and BTC...")
    since = datetime.now(timezone.utc) - timedelta(days=1460)
    
    # Fetch 1H data
    sol_1h = _fetch_ohlcv_ccxt("binance", "SOL/USDT", "1h", since=since, limit=100000)
    btc_1h = _fetch_ohlcv_ccxt("binance", "BTC/USDT", "1h", since=since, limit=100000)
    
    # Fetch 1D data
    sol_1d = _fetch_ohlcv_ccxt("binance", "SOL/USDT", "1d", since=since, limit=2000)
    
    # Calculate Macro ADX (Daily)
    sol_1d["daily_adx"] = _adx(sol_1d, 14)
    # Forward fill the daily ADX to the 1H timestamps
    # First, make sure daily timestamp is at start of day
    sol_1d["date"] = pd.to_datetime(sol_1d["timestamp"]).dt.date
    
    # Merge BTC into 1H
    btc_1h = btc_1h[["timestamp", "close"]].rename(columns={"close": "btc_close"})
    df = pd.merge(sol_1h, btc_1h, on="timestamp", how="left")
    
    # Merge Daily ADX into 1H
    df["date"] = pd.to_datetime(df["timestamp"]).dt.date
    df = pd.merge(df, sol_1d[["date", "daily_adx"]], on="date", how="left")
    # Shift daily_adx by 1 day to prevent look-ahead bias (we only know yesterday's closed ADX)
    df["daily_adx"] = df["daily_adx"].shift(24) # approx 24 hours shift
    df["daily_adx"] = df["daily_adx"].ffill()
    
    df["e200"] = _ema(df["close"], 200)
    df["e20"] = _ema(df["close"], 20)
    df["atr14"] = _atr(df, 14)
    df["v20"] = _sma(df["volume"], 20)
    df["btc_e200"] = _ema(df["btc_close"], 200)
    
    trades_original = []
    trades_macro_filtered = []
    
    last_bullish_cross_idx = 0
    i = 205
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
        
        daily_adx = float(df["daily_adx"].iloc[i]) if pd.notna(df["daily_adx"].iloc[i]) else 0
        
        if prev_e20 <= prev_e200 and e20_val > e200_val:
            last_bullish_cross_idx = i
            
        candle_range = h - l
        close_pct = (c - l) / candle_range if candle_range > 0 else 0
        dt = pd.to_datetime(df["timestamp"].iloc[i], utc=True)
        
        # Base Strategy: 1H Uptrend, Fast Retest, Strong Rejection, Volume, BTC Bullish, Midweek
        is_uptrend = e20_val > e200_val
        is_proper_speed = 20 <= (i - last_bullish_cross_idx) < 150
        is_touching = l <= e200_val and c > e200_val
        is_strong_rejection = close_pct > 0.6
        has_volume = (v / v_ma) > 1.2 if v_ma > 0 else False
        btc_bullish = btc_c > btc_e200_val
        is_midweek = dt.dayofweek in [1, 2, 3]
        
        if is_uptrend and is_proper_speed and is_touching and is_strong_rejection and has_volume and btc_bullish and is_midweek:
            sl = c - 1.5 * at
            tp = c + 15.0 * (c - sl)
            j = i + 1
            exit_idx = None
            result = None
            
            while j < len(df):
                if float(df["low"].iloc[j]) <= sl:
                    exit_idx, result = j, "LOSS"
                    break
                if float(df["high"].iloc[j]) >= tp:
                    exit_idx, result = j, "WIN"
                    break
                j += 1
                
            if exit_idx is not None:
                trade_info = {"date": dt.strftime('%Y-%m-%d'), "result": result, "daily_adx": daily_adx}
                trades_original.append(trade_info)
                
                # APPLY MACRO SIDEWAY FILTER: Daily ADX must be > 20 (meaning Macro market is NOT flat)
                if daily_adx > 20.0:
                    trades_macro_filtered.append(trade_info)
                    
                i = exit_idx
                continue
        i += 1
        
    print("\n--- BASELINE SOL RR 15 (LONG ONLY) ---")
    wins = len([t for t in trades_original if t["result"] == "WIN"])
    losses = len([t for t in trades_original if t["result"] == "LOSS"])
    total = len(trades_original)
    wr = wins / total * 100 if total else 0
    net = (wins * 15.0) - losses
    print(f"Trades: {total} | Wins: {wins} | Losses: {losses} | WR: {wr:.2f}% | Profit: {net:+.1f} R")

    print("\n--- SOL RR 15 + MACRO SIDEWAY FILTER (DAILY ADX > 20) ---")
    wins_m = len([t for t in trades_macro_filtered if t["result"] == "WIN"])
    losses_m = len([t for t in trades_macro_filtered if t["result"] == "LOSS"])
    total_m = len(trades_macro_filtered)
    wr_m = wins_m / total_m * 100 if total_m else 0
    net_m = (wins_m * 15.0) - losses_m
    print(f"Trades: {total_m} | Wins: {wins_m} | Losses: {losses_m} | WR: {wr_m:.2f}% | Profit: {net_m:+.1f} R")
    
    print("\n[Trades REMOVED by Macro Filter (Sideways Chopping):]")
    for t in trades_original:
        if t["daily_adx"] <= 20.0:
            print(f"- {t['date']} | Result: {t['result']} | Daily ADX: {t['daily_adx']:.1f} (SIDEWAY)")

if __name__ == "__main__":
    run_analysis()
