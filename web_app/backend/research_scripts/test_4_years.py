from datetime import datetime, timedelta, timezone
import pandas as pd
import numpy as np
from server.main import _fetch_ohlcv_ccxt, _sma, _rolling_low, _rolling_high, _ema, _atr, _adx

def _rsi(s, n=14):
    delta = s.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=n).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=n).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def test_4_years():
    print("Fetching 4 years (1460 days) of 1h data...")
    since = datetime.now(timezone.utc) - timedelta(days=1460)
    df = _fetch_ohlcv_ccxt("binance", "BTC/USDT", "1h", since=since, limit=50000)
    print(f"Loaded {len(df)} 1h candles.")

    fast = 9
    slow = 21
    rr = 2.0
    
    close = df["close"].astype(float)
    highs = df["high"].astype(float)
    lows = df["low"].astype(float)
    
    s_fast = _sma(close, fast)
    s_slow = _sma(close, slow)
    e200 = _ema(close, 200)

    cross_up = (s_fast > s_slow) & (s_fast.shift(1) <= s_slow.shift(1))

    atr = _atr(df, 14)
    rsi = _rsi(close, 14)

    sl_lookback = 10
    sl_low_base = _rolling_low(lows, sl_lookback).shift(1)

    trades = []
    i = max(fast, slow, 200, 28) + 2
    
    while i < len(df) - 1:
        entry = float(close.iloc[i])
        r = float(rsi.iloc[i]) if pd.notna(rsi.iloc[i]) else 0
        at = float(atr.iloc[i]) if pd.notna(atr.iloc[i]) else 0
        e2 = float(e200.iloc[i])
        
        # Only LONGs, Price > EMA200, RSI >= 50
        if bool(cross_up.iloc[i]) and entry > e2 and r >= 50:
            b = float(sl_low_base.iloc[i]) if pd.notna(sl_low_base.iloc[i]) else None
            if b:
                sl = b - at * 1.5
                risk = abs(entry - sl)
                
                if risk > 0:
                    tp = entry + rr * risk
                    j = i + 1
                    exit_idx = None
                    result = None
                    
                    while j < len(df):
                        hi = float(highs.iloc[j])
                        lo = float(lows.iloc[j])
                        if lo <= sl: exit_idx, result = j, "LOSS"; break
                        if hi >= tp: exit_idx, result = j, "WIN"; break
                        j += 1
                        
                    if exit_idx is not None:
                        trades.append({"entry_time": df["timestamp"].iloc[i], "entry": entry, "result": result})
                        i = exit_idx
        i += 1
        
    wins = [t for t in trades if t["result"] == "WIN"]
    losses = [t for t in trades if t["result"] == "LOSS"]
    total = len(trades)
    wr = len(wins) / total * 100 if total else 0
    
    print("\n--- 4 YEAR BACKTEST RESULTS (1H, SMA 9/21, EMA 200 LONG ONLY, RSI>50) ---")
    print(f"Total Trades: {total}")
    print(f"Wins: {len(wins)}")
    print(f"Losses: {len(losses)}")
    print(f"Winrate: {wr:.2f}% (RR = {rr})")

if __name__ == "__main__":
    test_4_years()
