from datetime import datetime, timedelta, timezone
import pandas as pd
import numpy as np
from server.main import _fetch_ohlcv_ccxt, _sma, _rolling_low, _rolling_high

def _ema(s, n): return s.ewm(span=n, adjust=False).mean()

def _atr(df, n=14):
    high, low, close_prev = df['high'], df['low'], df['close'].shift(1)
    tr = pd.concat([high - low, (high - close_prev).abs(), (low - close_prev).abs()], axis=1).max(axis=1)
    return tr.rolling(n).mean()

def _adx(df, n=14):
    up = df['high'] - df['high'].shift(1)
    down = df['low'].shift(1) - df['low']
    pos_dm = pd.Series(np.where((up > down) & (up > 0), up, 0))
    neg_dm = pd.Series(np.where((down > up) & (down > 0), down, 0))
    tr = _atr(df, 1)
    def wilder_smooth(s, n):
        res = np.zeros(len(s))
        res[0] = np.nan
        first = s.first_valid_index()
        if first is None: return pd.Series(res)
        res[first+n-1] = s.iloc[first:first+n].sum()
        for i in range(first+n, len(s)):
            res[i] = res[i-1] - (res[i-1]/n) + s.iloc[i]
        return pd.Series(res, index=s.index)
    atr_smooth = wilder_smooth(tr, n)
    pos_di = 100 * (wilder_smooth(pos_dm, n) / atr_smooth)
    neg_di = 100 * (wilder_smooth(neg_dm, n) / atr_smooth)
    dx = 100 * ((pos_di - neg_di).abs() / (pos_di + neg_di))
    return wilder_smooth(dx, n)

def _rsi(s, n=14):
    delta = s.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=n).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=n).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def run_test(df, use_volume, use_rsi, break_even):
    close = df["close"].astype(float)
    highs = df["high"].astype(float)
    lows = df["low"].astype(float)
    vol = df["volume"].astype(float)
    
    s_fast = _sma(close, 9)
    s_slow = _sma(close, 21)
    ema200 = _ema(close, 200)
    vol_ma = _sma(vol, 20)
    rsi = _rsi(close, 14)

    cross_up = (s_fast > s_slow) & (s_fast.shift(1) <= s_slow.shift(1))
    cross_dn = (s_fast < s_slow) & (s_fast.shift(1) >= s_slow.shift(1))

    df['ATR'] = _atr(df, 14)
    df['ADX'] = _adx(df, 14)

    sl_lookback = 10
    sl_low_base = _rolling_low(lows, sl_lookback).shift(1)
    sl_high_base = _rolling_high(highs, sl_lookback).shift(1)

    trades = []
    i = 0
    min_i = max(200, 28) + 2
    
    while i < len(df):
        if i < min_i:
            i += 1
            continue

        entry = float(close.iloc[i])
        adx = float(df["ADX"].iloc[i]) if pd.notna(df["ADX"].iloc[i]) else 0
        atr = float(df["ATR"].iloc[i]) if pd.notna(df["ATR"].iloc[i]) else 0
        e200 = float(ema200.iloc[i])
        v = float(vol.iloc[i])
        vma = float(vol_ma.iloc[i])
        r = float(rsi.iloc[i])

        side = None
        sl = None
        
        # filters
        trend_up = entry > e200
        trend_dn = entry < e200
        
        vol_ok = (v > vma * 1.2) if use_volume else True
        rsi_long_ok = (r < 70) if use_rsi else True
        rsi_short_ok = (r > 30) if use_rsi else True

        if bool(cross_up.iloc[i]) and adx > 20 and trend_up and vol_ok and rsi_long_ok:
            side = "LONG"
            b = float(sl_low_base.iloc[i]) if pd.notna(sl_low_base.iloc[i]) else None
            if b: sl = b - atr * 1.5
        elif bool(cross_dn.iloc[i]) and adx > 20 and trend_dn and vol_ok and rsi_short_ok:
            side = "SHORT"
            b = float(sl_high_base.iloc[i]) if pd.notna(sl_high_base.iloc[i]) else None
            if b: sl = b + atr * 1.5

        if side is None or sl is None:
            i += 1
            continue

        risk = abs(entry - sl)
        if risk <= 0:
            i += 1
            continue

        rr = 1.0 # fixed RR for this test to push winrate
        tp = entry + rr * risk if side == "LONG" else entry - rr * risk
        be_target = entry + 0.5 * risk if side == "LONG" else entry - 0.5 * risk

        exit_idx = None
        result = None
        current_sl = sl

        j = i + 1
        while j < len(df):
            hi = float(highs.iloc[j])
            lo = float(lows.iloc[j])
            
            if side == "LONG":
                if break_even and hi >= be_target:
                    current_sl = max(current_sl, entry) # move to BE
                    
                if lo <= current_sl: 
                    exit_idx = j
                    result = "BE" if current_sl == entry else "LOSS"
                    break
                if hi >= tp: 
                    exit_idx, result = j, "WIN"
                    break
            else:
                if break_even and lo <= be_target:
                    current_sl = min(current_sl, entry) # move to BE
                    
                if hi >= current_sl: 
                    exit_idx = j
                    result = "BE" if current_sl == entry else "LOSS"
                    break
                if lo <= tp: 
                    exit_idx, result = j, "WIN"
                    break
            j += 1

        if exit_idx is None:
            i += 1
            continue

        trades.append({"result": result})
        i = exit_idx + 1

    wins = [t for t in trades if t["result"] == "WIN"]
    losses = [t for t in trades if t["result"] == "LOSS"]
    bes = [t for t in trades if t["result"] == "BE"]
    
    total = len(trades)
    wr = len(wins) / total * 100 if total else 0
    return total, len(wins), len(losses), len(bes), wr

def main():
    since = datetime.now(timezone.utc) - timedelta(days=60)
    df = _fetch_ohlcv_ccxt("binance", "BTC/USDT", "15m", since=since, limit=50000)
    
    scenarios = [
        {"vol": False, "rsi": False, "be": False},
        {"vol": True,  "rsi": False, "be": False},
        {"vol": False, "rsi": True,  "be": False},
        {"vol": False, "rsi": False, "be": True},
        {"vol": True,  "rsi": True,  "be": True},
    ]

    for s in scenarios:
        tot, w, l, b, wr = run_test(df, s['vol'], s['rsi'], s['be'])
        print(f"Vol:{str(s['vol'])[0]} RSI:{str(s['rsi'])[0]} BE:{str(s['be'])[0]} -> Trades: {tot:03d} (W:{w} L:{l} BE:{b}) | Winrate: {wr:.2f}%")

if __name__ == "__main__":
    main()
