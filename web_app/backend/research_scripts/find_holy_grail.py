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

def test_strategy(df, fast, slow, adx_thresh, rsi_min, rsi_max, pullback_entry):
    close = df["close"]
    highs = df["high"]
    lows = df["low"]
    
    s_fast = _sma(close, fast)
    s_slow = _sma(close, slow)
    e200 = _ema(close, 200)

    cross_up = (s_fast > s_slow) & (s_fast.shift(1) <= s_slow.shift(1))
    cross_dn = (s_fast < s_slow) & (s_fast.shift(1) >= s_slow.shift(1))

    atr = _atr(df, 14)
    adx = _adx(df, 14)
    rsi = _rsi(close, 14)

    sl_lookback = 10
    sl_low_base = _rolling_low(lows, sl_lookback).shift(1)
    sl_high_base = _rolling_high(highs, sl_lookback).shift(1)

    trades = []
    i = max(fast, slow, 200, 28) + 2
    
    while i < len(df) - 1:
        if bool(cross_up.iloc[i]) or bool(cross_dn.iloc[i]):
            a = adx.iloc[i]
            r = rsi.iloc[i]
            c = close.iloc[i]
            e = e200.iloc[i]
            
            if pd.isna(a) or pd.isna(r) or pd.isna(e):
                i += 1
                continue

            if a < adx_thresh:
                i += 1
                continue
                
            if not (rsi_min <= r <= rsi_max):
                i += 1
                continue

            side = None
            if bool(cross_up.iloc[i]) and c > e:
                side = "LONG"
            elif bool(cross_dn.iloc[i]) and c < e:
                side = "SHORT"

            if side:
                # Limit order logic
                entry_price = float(c)
                if pullback_entry:
                    entry_price = float(s_fast.iloc[i]) # limit order at SMA fast
                    
                at = float(atr.iloc[i])
                if side == "LONG":
                    b = float(sl_low_base.iloc[i])
                    sl = b - at * 1.5
                else:
                    b = float(sl_high_base.iloc[i])
                    sl = b + at * 1.5
                    
                risk = abs(entry_price - sl)
                if risk <= 0:
                    i += 1
                    continue
                    
                rr = 2.0
                tp = entry_price + rr * risk if side == "LONG" else entry_price - rr * risk
                
                # Check outcome
                j = i + 1
                exit_idx = None
                result = None
                filled = not pullback_entry
                
                while j < len(df):
                    hi = float(highs.iloc[j])
                    lo = float(lows.iloc[j])
                    
                    if not filled:
                        if side == "LONG" and lo <= entry_price:
                            filled = True
                        elif side == "SHORT" and hi >= entry_price:
                            filled = True
                        
                        # If cross opposite before filled, cancel order
                        if side == "LONG" and bool(cross_dn.iloc[j]): break
                        if side == "SHORT" and bool(cross_up.iloc[j]): break
                            
                    if filled:
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
    losses = trades.count("LOSS")
    total = wins + losses
    wr = wins / total * 100 if total else 0
    return total, wins, wr

def main():
    print("Fetching 180 days of 1h data for stability...")
    since = datetime.now(timezone.utc) - timedelta(days=180)
    df = _fetch_ohlcv_ccxt("binance", "BTC/USDT", "1h", since=since, limit=50000)
    print(f"Loaded {len(df)} 1h candles.")
    
    print(f"{'F/S':<7} | {'ADX':<3} | {'RSI':<7} | {'Pullback':<8} | {'Trades':<6} | {'WR%':<5}")
    for fast, slow in [(9,21), (20,50), (50,200)]:
        for adx in [0, 20, 25, 30]:
            for rsi_min, rsi_max in [(0,100), (40, 60), (30, 70), (50, 100)]:
                for pb in [False, True]:
                    tot, w, wr = test_strategy(df, fast, slow, adx, rsi_min, rsi_max, pb)
                    if tot > 10 and wr > 50:
                        print(f"{fast}/{slow:<3} | {adx:<3} | {rsi_min}-{rsi_max:<4} | {pb!s:<8} | {tot:<6} | {wr:.2f}%")

if __name__ == "__main__":
    main()
