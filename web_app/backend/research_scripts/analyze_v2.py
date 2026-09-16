from datetime import datetime, timedelta, timezone
import pandas as pd
import numpy as np
from server.main import _fetch_ohlcv_ccxt, _sma, _rolling_low, _rolling_high

def _atr(df, n=14):
    high = df['high']
    low = df['low']
    close_prev = df['close'].shift(1)
    
    tr1 = high - low
    tr2 = (high - close_prev).abs()
    tr3 = (low - close_prev).abs()
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    # Simple moving average of TR
    atr = tr.rolling(window=n).mean()
    return atr

def _adx(df, n=14):
    high = df['high']
    low = df['low']
    close = df['close']
    
    up = high - high.shift(1)
    down = low.shift(1) - low
    
    pos_dm = pd.Series(np.where((up > down) & (up > 0), up, 0))
    neg_dm = pd.Series(np.where((down > up) & (down > 0), down, 0))
    
    tr = _atr(df, 1) # True Range for 1 period
    
    # Wilder's Smoothing
    def wilder_smooth(s, n):
        res = np.zeros(len(s))
        res[0] = np.nan
        # first non-nan
        first_valid = s.first_valid_index()
        if first_valid is None: return pd.Series(res)
        res[first_valid+n-1] = s.iloc[first_valid:first_valid+n].sum()
        for i in range(first_valid+n, len(s)):
            res[i] = res[i-1] - (res[i-1]/n) + s.iloc[i]
        return pd.Series(res, index=s.index)
        
    atr_smooth = wilder_smooth(tr, n)
    pos_dm_smooth = wilder_smooth(pos_dm, n)
    neg_dm_smooth = wilder_smooth(neg_dm, n)
    
    pos_di = 100 * (pos_dm_smooth / atr_smooth)
    neg_di = 100 * (neg_dm_smooth / atr_smooth)
    
    dx = 100 * ((pos_di - neg_di).abs() / (pos_di + neg_di))
    adx = wilder_smooth(dx, n)
    
    return adx

def analyze():
    print("Fetching data...")
    symbol = "BTC/USDT"
    timeframe = "15m"
    days_back = 30
    since = datetime.now(timezone.utc) - timedelta(days=days_back)
    
    df = _fetch_ohlcv_ccxt("binance", symbol, timeframe, since=since, limit=50000)
    print(f"Fetched {len(df)} rows.")

    fast = 20
    slow = 50
    sl_lookback = 10
    rr = 2.0

    close = df["close"].astype(float)
    highs = df["high"].astype(float)
    lows = df["low"].astype(float)
    
    s_fast = _sma(close, fast)
    s_slow = _sma(close, slow)

    cross_up = (s_fast > s_slow) & (s_fast.shift(1) <= s_slow.shift(1))
    cross_dn = (s_fast < s_slow) & (s_fast.shift(1) >= s_slow.shift(1))

    df['ATR'] = _atr(df, 14)
    df['ADX'] = _adx(df, 14)

    sl_low_base = _rolling_low(lows, sl_lookback).shift(1)
    sl_high_base = _rolling_high(highs, sl_lookback).shift(1)

    trades = []
    i = 0
    min_i = max(fast, slow, sl_lookback, 14*2) + 2
    
    while i < len(df):
        if i < min_i:
            i += 1
            continue

        entry = float(close.iloc[i])
        ts_entry = df["timestamp"].iloc[i]
        
        adx = float(df["ADX"].iloc[i]) if pd.notna(df["ADX"].iloc[i]) else 0
        atr = float(df["ATR"].iloc[i]) if pd.notna(df["ATR"].iloc[i]) else 0

        side = None
        sl = None
        
        if bool(cross_up.iloc[i]) and adx > 20:
            side = "LONG"
            base_sl = float(sl_low_base.iloc[i]) if pd.notna(sl_low_base.iloc[i]) else None
            if base_sl:
                sl = base_sl - (atr * 1.5)
        elif bool(cross_dn.iloc[i]) and adx > 20:
            side = "SHORT"
            base_sl = float(sl_high_base.iloc[i]) if pd.notna(sl_high_base.iloc[i]) else None
            if base_sl:
                sl = base_sl + (atr * 1.5)

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
                sl_hit = lo <= sl
                tp_hit = hi >= tp
                if sl_hit and tp_hit:
                    exit_idx, result = j, "LOSS"
                    break
                if sl_hit:
                    exit_idx, result = j, "LOSS"
                    break
                if tp_hit:
                    exit_idx, result = j, "WIN"
                    break
            else:
                sl_hit = hi >= sl
                tp_hit = lo <= tp
                if sl_hit and tp_hit:
                    exit_idx, result = j, "LOSS"
                    break
                if sl_hit:
                    exit_idx, result = j, "LOSS"
                    break
                if tp_hit:
                    exit_idx, result = j, "WIN"
                    break
            j += 1

        if exit_idx is None:
            i += 1
            continue

        trades.append({"side": side, "result": result})
        i = exit_idx + 1

    wins = [t for t in trades if t["result"] == "WIN"]
    losses = [t for t in trades if t["result"] == "LOSS"]

    print(f"\n--- NEW BACKTEST SUMMARY (ADX > 20 + ATR SL) ---")
    print(f"Total Trades: {len(trades)}")
    print(f"Wins: {len(wins)}, Losses: {len(losses)}")
    winrate = len(wins) / len(trades) * 100 if trades else 0
    print(f"Winrate: {winrate:.2f}%\n")

if __name__ == "__main__":
    analyze()
