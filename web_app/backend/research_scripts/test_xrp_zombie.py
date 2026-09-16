from datetime import datetime, timedelta, timezone
import pandas as pd
import numpy as np
from server.main import _fetch_ohlcv_ccxt, _sma, _ema, _atr

def test_xrp():
    print("Fetching 4 years of 30m data for XRP/USDT...")
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
    bbw = (bb_upper - bb_lower) / sma20 * 100 # Bollinger Band Width (%)
    
    atr14 = _atr(df, 14)
    v20 = _sma(vol, 20)
    e200 = _ema(close, 200)
    
    trades = []
    i = 205
    
    cond_sleep = 0
    cond_breakout = 0
    cond_vol = 0
    cond_all = 0
    
    while i < len(df) - 1:
        c = float(close.iloc[i])
        h = float(high.iloc[i])
        l = float(low.iloc[i])
        v = float(vol.iloc[i])
        v_ma = float(v20.iloc[i]) if pd.notna(v20.iloc[i]) else 0
        b_up = float(bb_upper.iloc[i])
        e2 = float(e200.iloc[i])
        at = float(atr14.iloc[i]) if pd.notna(atr14.iloc[i]) else 0
        
        # Squeeze definition: Bollinger Band Width < 1.0% in the last 5 candles
        # XRP is cheap, 1.0% width is extremely tight.
        bbw_sleep = False
        if i >= 5:
            recent_bbw = bbw.iloc[i-5:i]
            if not recent_bbw.isna().any() and recent_bbw.min() < 1.2:
                bbw_sleep = True
                
        if bbw_sleep: cond_sleep += 1
        
        if bbw_sleep and c > b_up: cond_breakout += 1
        
        vol_mult = v / v_ma if v_ma > 0 else 0
        
        if bbw_sleep and c > b_up and vol_mult > 3.0: cond_vol += 1
        
        if bbw_sleep and c > b_up and vol_mult > 3.0 and c > e2:
            cond_all += 1
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
                    trades.append(result)
                    i = exit_idx
        i += 1
        
    print(f"Passed BBW Sleep (< 1.2%): {cond_sleep}")
    print(f"Passed Breakout BB: {cond_breakout}")
    print(f"Passed Volume > 3.0x: {cond_vol}")
    print(f"Total Entries (also C > E200): {cond_all}")
    
    wins = trades.count("WIN")
    losses = trades.count("LOSS")
    total = len(trades)
    wr = wins / total * 100 if total else 0
    net_r = wins * 10.0 - losses * 1.0
    
    print("\n--- XRP ZOMBIE AWAKENING (30M) RR = 10.0 ---")
    print(f"Total Trades: {total}")
    print(f"Wins: {wins}")
    print(f"Losses: {losses}")
    print(f"Winrate: {wr:.2f}%")
    print(f"Net Profit: {net_r:+.2f}R")

if __name__ == "__main__":
    test_xrp()
