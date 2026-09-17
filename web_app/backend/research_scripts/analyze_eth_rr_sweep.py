from datetime import datetime, timedelta, timezone
import pandas as pd
from server.main import _fetch_ohlcv_ccxt, _sma, _ema, _atr

def run_analysis():
    print("Fetching 4 years of 1h data for ETH (LONG ONLY RR SWEEP)...")
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

    print("\n--- ETH SQUEEZE BREAKOUT (LONG ONLY) RR SWEEP ---")
    
    rr_sweep = [2.0, 3.0, 4.0, 5.0, 7.0, 10.0, 12.0, 15.0]
    
    for rr in rr_sweep:
        w_cnt = 0
        l_cnt = 0
        skip_idx = 0
        
        for i in range(205, len(df)-1):
            if i < skip_idx: continue
            
            c = float(close.iloc[i])
            h = float(high.iloc[i])
            l = float(low.iloc[i])
            v = float(vol.iloc[i])
            v_ma = float(v20.iloc[i]) if pd.notna(v20.iloc[i]) else 0
            b_up = float(bb_upper.iloc[i])
            e2 = float(e200.iloc[i])
            at = float(atr14.iloc[i]) if pd.notna(atr14.iloc[i]) else 0
            dt = pd.to_datetime(df["timestamp"].iloc[i], utc=True)

            recent_squeeze = is_squeeze.iloc[i-3:i+1].any()
            max_duration = df['squeeze_duration'].iloc[i-10:i+1].max()
            vol_mult = v / v_ma if v_ma > 0 else 0
            dist_e200 = (c - e2) / e2 * 100
            candle_size_pct = (h - l) / c * 100

            if recent_squeeze and c > b_up and (2.0 < vol_mult < 3.0) and c > e2 and dt.dayofweek != 0 and dist_e200 >= 1.0 and max_duration < 6 and candle_size_pct < 2.0:
                entry = c
                sl = l
                if (entry - sl) < 0.3 * at:
                    sl = entry - 0.5 * at

                risk = entry - sl
                if risk > 0:
                    tp = entry + rr * risk
                    j = i + 1
                    exit_idx = None
                    result = None
                    
                    while j < len(df):
                        hi = float(high.iloc[j])
                        lo = float(low.iloc[j])
                        if lo <= sl: 
                            exit_idx, result = j, "LOSS"
                            break
                        if hi >= tp: 
                            exit_idx, result = j, "WIN"
                            break
                        j += 1

                    if exit_idx is not None:
                        if result == "WIN": w_cnt += 1
                        else: l_cnt += 1
                        skip_idx = exit_idx
        
        tot = w_cnt + l_cnt
        wr = w_cnt / tot * 100 if tot else 0
        net = (w_cnt * rr) - l_cnt
        print(f"RR: {rr:>4.1f} | Trades: {tot:>2} | Wins: {w_cnt:>2} | Losses: {l_cnt:>2} | WR: {wr:05.2f}% | Net Profit: {net:>+6.1f} R")

if __name__ == "__main__":
    run_analysis()
