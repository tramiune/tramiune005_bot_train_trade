from datetime import datetime, timedelta, timezone
import pandas as pd
import numpy as np
from server.main import _fetch_ohlcv_ccxt, _sma, _rolling_low, _rolling_high, _ema, _atr, _adx

def test_rr(df, rr):
    close = df["close"].astype(float)
    highs = df["high"].astype(float)
    lows = df["low"].astype(float)
    
    s_fast = _sma(close, 9)
    s_slow = _sma(close, 21)
    e200 = _ema(close, 200)

    cross_up = (s_fast > s_slow) & (s_fast.shift(1) <= s_slow.shift(1))
    cross_dn = (s_fast < s_slow) & (s_fast.shift(1) >= s_slow.shift(1))

    atr = _atr(df, 14)
    adx = _adx(df, 14)

    sl_lookback = 10
    sl_low_base = _rolling_low(lows, sl_lookback).shift(1)
    sl_high_base = _rolling_high(highs, sl_lookback).shift(1)

    trades = []
    i = 205
    
    while i < len(df) - 1:
        entry = float(close.iloc[i])
        a = float(adx.iloc[i]) if pd.notna(adx.iloc[i]) else 0
        at = float(atr.iloc[i]) if pd.notna(atr.iloc[i]) else 0
        e2 = float(e200.iloc[i])

        side = None
        sl = None
        
        if bool(cross_up.iloc[i]) and a > 20 and entry > e2:
            side = "LONG"
            b = float(sl_low_base.iloc[i]) if pd.notna(sl_low_base.iloc[i]) else None
            if b: sl = b - at * 1.5
        elif bool(cross_dn.iloc[i]) and a > 20 and entry < e2:
            side = "SHORT"
            b = float(sl_high_base.iloc[i]) if pd.notna(sl_high_base.iloc[i]) else None
            if b: sl = b + at * 1.5

        if side is None or sl is None:
            i += 1
            continue

        risk = abs(entry - sl)
        if risk <= 0:
            i += 1
            continue

        tp = entry + rr * risk if side == "LONG" else entry - rr * risk

        exit_idx = None
        result = None

        j = i + 1
        while j < len(df):
            hi = float(highs.iloc[j])
            lo = float(lows.iloc[j])
            if side == "LONG":
                if lo <= sl: exit_idx, result = j, "LOSS"; break
                if hi >= tp: exit_idx, result = j, "WIN"; break
            else:
                if hi >= sl: exit_idx, result = j, "LOSS"; break
                if lo <= tp: exit_idx, result = j, "WIN"; break
            j += 1

        if exit_idx is not None:
            trades.append(result)
            i = exit_idx
        i += 1
        
    wins = trades.count("WIN")
    total = len(trades)
    wr = wins / total * 100 if total else 0
    return total, wr

def main():
    since = datetime.now(timezone.utc) - timedelta(days=60)
    df = _fetch_ohlcv_ccxt("binance", "BTC/USDT", "15m", since=since, limit=50000)
    
    for r in [2.0, 1.5, 1.0, 0.8, 0.5, 0.3]:
        tot, wr = test_rr(df, r)
        print(f"RR = {r:<3} -> Trades: {tot:<3} | Winrate: {wr:.2f}%")

if __name__ == "__main__":
    main()
