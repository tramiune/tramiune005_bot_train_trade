import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from datetime import datetime, timedelta, timezone
import pandas as pd
import numpy as np
from server.main import _fetch_ohlcv_ccxt, _sma, _ema, _atr

def get_sol_v2_sequence():
    since = datetime.now(timezone.utc) - timedelta(days=1460)
    df = _fetch_ohlcv_ccxt("binance", "SOL/USDT", "1h", since=since, limit=100000)
    btc = _fetch_ohlcv_ccxt("binance", "BTC/USDT", "1h", since=since, limit=100000)
    btc = btc[["timestamp", "close"]].rename(columns={"close": "btc_close"})
    df = pd.merge(df, btc, on="timestamp", how="left")
    
    df["e200"] = _ema(df["close"].astype(float), 200)
    df["e20"] = _ema(df["close"].astype(float), 20)
    df["atr14"] = _atr(df, 14)
    df["v20"] = _sma(df["volume"].astype(float), 20)
    df["btc_e200"] = _ema(df["btc_close"].astype(float), 200)
    
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
            
        close_pct = (c - l) / (h - l) if (h - l) > 0 else 0
        dt = pd.to_datetime(df["timestamp"].iloc[i], utc=True)
        
        # EXACT deployed filters
        is_uptrend = e20_val > e200_val
        candles_since_cross = i - last_bullish_cross_idx
        is_proper_speed = 20 <= candles_since_cross < 150
        is_touching = l <= e200_val and c > e200_val
        is_strong_rejection = close_pct > 0.6
        has_volume = (v / v_ma) > 1.2 if v_ma > 0 else False
        btc_bullish = btc_c > btc_e200_val
        is_midweek = dt.dayofweek in [1, 2, 3] # Tue, Wed, Thu
        
        if is_uptrend and is_proper_speed and is_touching and is_strong_rejection and has_volume and btc_bullish and is_midweek:
            sl = c - 1.5 * at
            tp = c + rr_target * (c - sl)
            j = i + 1
            exit_idx = None
            result = None
            while j < len(df):
                if float(df["low"].iloc[j]) <= sl: exit_idx, result = j, "LOSS"; break
                if float(df["high"].iloc[j]) >= tp: exit_idx, result = j, "WIN"; break
                j += 1
            if exit_idx is not None:
                trades.append(result)
                i = exit_idx
                continue
        i += 1
    return trades

def run_simulation():
    trades = get_sol_v2_sequence()
    print(f"EXACT DEPLOYED SEQUENCE ({len(trades)} trades): {trades}")
    
    cap = 10_000_000
    risk = 0.10
    
    for idx, t in enumerate(trades):
        if t == "WIN":
            profit = cap * risk * 15.0
            cap += profit
            print(f"Trade {idx+1} [WIN]:  +{profit:,.0f} -> Cap: {cap:,.0f}")
        else:
            loss = cap * risk
            cap -= loss
            print(f"Trade {idx+1} [LOSS]: -{loss:,.0f} -> Cap: {cap:,.0f}")
            
    print(f"\nFINAL CAPITAL: {cap:,.0f} VND")
    
if __name__ == "__main__":
    run_simulation()
