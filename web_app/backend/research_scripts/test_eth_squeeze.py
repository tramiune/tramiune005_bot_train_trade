from datetime import datetime, timedelta, timezone
import pandas as pd
import numpy as np
from server.main import _fetch_ohlcv_ccxt, _sma, _ema, _atr

def test_eth_squeeze():
    print("Fetching 4 years of 1h data for ETH/USDT Squeeze Breakout...")
    since = datetime.now(timezone.utc) - timedelta(days=1460)
    df = _fetch_ohlcv_ccxt("binance", "ETH/USDT", "1h", since=since, limit=50000)
    
    close = df["close"].astype(float)
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    vol = df["volume"].astype(float)
    
    # Bollinger Bands (20, 2)
    sma20 = _sma(close, 20)
    std20 = close.rolling(20).std()
    bb_upper = sma20 + 2 * std20
    bb_lower = sma20 - 2 * std20
    
    # Keltner Channels (20, 1.5)
    ema20 = _ema(close, 20)
    atr20 = _atr(df, 20)
    kc_upper = ema20 + 1.5 * atr20
    kc_lower = ema20 - 1.5 * atr20
    
    atr14 = _atr(df, 14)
    v20 = _sma(vol, 20)
    e200 = _ema(close, 200)

    # Squeeze condition: BB is inside KC
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
        
        # Check if there was a squeeze in the last 3 candles
        recent_squeeze = is_squeeze.iloc[i-3:i+1].any()
        
        # Long Breakout:
        # 1. Recent squeeze
        # 2. Breakout above BB upper
        # 3. Volume spike
        # 4. Uptrend
        if recent_squeeze and c > b_up and v > 1.5 * v_ma and c > e2:
            entry = c
            
            # Super tight Stoploss: Low of the breakout candle. 
            # If the candle is too small, use 0.5 * ATR to give minimal breathing room.
            sl = l
            if (entry - sl) < 0.3 * at:
                sl = entry - 0.5 * at
                
            risk = entry - sl
            if risk > 0:
                rr = 5.0
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
    net_r = wins * 5.0 - losses * 1.0
    
    print("\n--- ETH/USDT SQUEEZE BREAKOUT (RR = 5.0) ---")
    print(f"Total Trades: {total}")
    print(f"Wins: {wins}")
    print(f"Losses: {losses}")
    print(f"Winrate: {wr:.2f}%")
    print(f"Net Profit: {net_r:+.2f}R")

if __name__ == "__main__":
    test_eth_squeeze()
