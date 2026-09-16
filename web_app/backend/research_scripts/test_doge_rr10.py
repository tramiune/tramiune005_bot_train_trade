from datetime import datetime, timedelta, timezone
import pandas as pd
import numpy as np
from server.main import _fetch_ohlcv_ccxt, _sma, _ema, _atr

def test_doge():
    print("Fetching 4 years of 1h data for DOGE/USDT...")
    since = datetime.now(timezone.utc) - timedelta(days=1460)
    df = _fetch_ohlcv_ccxt("binance", "DOGE/USDT", "1h", since=since, limit=100000)
    
    close = df["close"].astype(float)
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    vol = df["volume"].astype(float)
    
    sma20 = _sma(close, 20)
    std20 = close.rolling(20).std()
    bb_upper = sma20 + 2 * std20
    bb_lower = sma20 - 2 * std20
    
    ema20 = _ema(close, 20)
    atr20 = _atr(df, 20)
    kc_upper = ema20 + 1.5 * atr20
    kc_lower = ema20 - 1.5 * atr20
    
    atr14 = _atr(df, 14)
    v20 = _sma(vol, 20)
    e200 = _ema(close, 200)
    
    is_squeeze = (bb_upper < kc_upper) & (bb_lower > kc_lower)
    
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
        
        recent_squeeze = is_squeeze.iloc[i-3:i+1].any()
        vol_mult = v / v_ma if v_ma > 0 else 0
        
        if recent_squeeze and c > b_up and vol_mult > 3.0 and c > e2:
            entry = c
            
            # WIDE STOPLOSS FOR DOGE WILD PULLBACKS
            sl = entry - 2.5 * at
                
            risk = entry - sl
            if risk > 0:
                rr = 10.0  # RR 10
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
        
    wins = trades.count("WIN")
    losses = trades.count("LOSS")
    total = len(trades)
    wr = wins / total * 100 if total else 0
    net_r = (wins * 10.0) - (losses * 1.0)
    
    print("\n--- DOGE AWAKENING (1H) RR = 10.0 (WIDE SL) ---")
    print(f"Total Trades: {total}")
    print(f"Wins: {wins}")
    print(f"Losses: {losses}")
    print(f"Winrate: {wr:.2f}%")
    print(f"Net Profit: +{net_r:.2f}R")

if __name__ == "__main__":
    test_doge()
