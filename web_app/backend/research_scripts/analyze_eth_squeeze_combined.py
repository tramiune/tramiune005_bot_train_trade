from datetime import datetime, timedelta, timezone
import pandas as pd
from server.main import _fetch_ohlcv_ccxt, _sma, _ema, _atr

def run_analysis():
    print("Fetching 4 years of 1h data for ETH (LONG + SHORT)...")
    since = datetime.now(timezone.utc) - timedelta(days=1460)
    df = _fetch_ohlcv_ccxt("binance", "ETH/USDT", "1h", since=since, limit=100000)
    
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
    
    squeeze_durations = []
    current_duration = 0
    for val in is_squeeze:
        if val:
            current_duration += 1
        else:
            current_duration = 0
        squeeze_durations.append(current_duration)
    df['squeeze_duration'] = squeeze_durations

    trades = []
    i = 205
    rr = 5.0

    while i < len(df) - 1:
        c = float(close.iloc[i])
        h = float(high.iloc[i])
        l = float(low.iloc[i])
        v = float(vol.iloc[i])
        v_ma = float(v20.iloc[i]) if pd.notna(v20.iloc[i]) else 0
        b_up = float(bb_upper.iloc[i])
        b_dn = float(bb_lower.iloc[i])
        e2 = float(e200.iloc[i])
        at = float(atr14.iloc[i]) if pd.notna(atr14.iloc[i]) else 0
        dt = pd.to_datetime(df["timestamp"].iloc[i], utc=True)

        recent_squeeze = is_squeeze.iloc[i-3:i+1].any()
        max_duration = df['squeeze_duration'].iloc[i-10:i+1].max()
        vol_mult = v / v_ma if v_ma > 0 else 0
        candle_size_pct = (h - l) / c * 100
        
        # Long Logic
        dist_e200_long = (c - e2) / e2 * 100
        is_long = recent_squeeze and c > b_up and (2.0 < vol_mult < 3.0) and c > e2 and dt.dayofweek != 0 and dist_e200_long >= 1.0 and max_duration < 6 and candle_size_pct < 2.0
        
        # Short Logic
        dist_e200_short = (e2 - c) / e2 * 100
        is_short = recent_squeeze and c < b_dn and (2.0 < vol_mult < 3.0) and c < e2 and dt.dayofweek != 0 and dist_e200_short >= 1.0 and max_duration < 6 and candle_size_pct < 2.0

        if is_long:
            entry = c
            sl = l
            if (entry - sl) < 0.3 * at:
                sl = entry - 0.5 * at
            risk = entry - sl
            if risk > 0:
                tp = entry + rr * risk
                j = i + 1
                exit_idx, result = None, None
                while j < len(df):
                    hi = float(high.iloc[j])
                    lo = float(low.iloc[j])
                    if lo <= sl: exit_idx, result = j, "LOSS"; break
                    if hi >= tp: exit_idx, result = j, "WIN"; break
                    j += 1
                if exit_idx is not None:
                    trades.append({"type": "LONG", "time": dt, "result": result})
                    i = exit_idx
                    continue
                    
        elif is_short:
            entry = c
            sl = h
            if (sl - entry) < 0.3 * at:
                sl = entry + 0.5 * at
            risk = sl - entry
            if risk > 0:
                tp = entry - rr * risk
                j = i + 1
                exit_idx, result = None, None
                while j < len(df):
                    hi = float(high.iloc[j])
                    lo = float(low.iloc[j])
                    if hi >= sl: exit_idx, result = j, "LOSS"; break
                    if lo <= tp: exit_idx, result = j, "WIN"; break
                    j += 1
                if exit_idx is not None:
                    trades.append({"type": "SHORT", "time": dt, "result": result})
                    i = exit_idx
                    continue
        i += 1

    longs = [t for t in trades if t["type"] == "LONG"]
    shorts = [t for t in trades if t["type"] == "SHORT"]
    
    print("\n--- ETH SQUEEZE BREAKOUT RR 5.0 (UNIFIED LONG + SHORT) ---")
    
    for label, subset in [("LONG", longs), ("SHORT", shorts), ("TOTAL", trades)]:
        wins = len([t for t in subset if t["result"] == "WIN"])
        losses = len([t for t in subset if t["result"] == "LOSS"])
        total = len(subset)
        wr = wins / total * 100 if total else 0
        net = (wins * rr) - losses
        print(f"\n[{label} STATS]")
        print(f"Trades: {total} | Wins: {wins} | Losses: {losses}")
        print(f"Winrate: {wr:.2f}%")
        print(f"Net Profit: {net:+.1f} R")

if __name__ == "__main__":
    run_analysis()
