from datetime import datetime, timedelta, timezone
import pandas as pd
from server.main import _fetch_ohlcv_ccxt, _sma, _ema, _atr

def run_analysis():
    print("Fetching 4 years of 1h data for ETH...")
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
                    trades.append({
                        "entry_time": dt,
                        "result": result,
                        "sl_dist_pct": risk / entry * 100
                    })
                    i = exit_idx
                    continue
        i += 1

    wins = [t for t in trades if t["result"] == "WIN"]
    losses = [t for t in trades if t["result"] == "LOSS"]
    total = len(trades)
    wr = len(wins) / total * 100 if total else 0
    net = (len(wins) * rr) - len(losses)
    
    print(f"\n--- ETH SQUEEZE BREAKOUT (RR 5.0) ---")
    print(f"Total Trades: {total}")
    print(f"Wins: {len(wins)}")
    print(f"Losses: {len(losses)}")
    print(f"Winrate: {wr:.2f}%")
    print(f"Net Profit: +{net} R")
    
    # Calculate Drawdown
    max_losses = 0
    current_losses = 0
    for t in trades:
        if t["result"] == "LOSS":
            current_losses += 1
        else:
            if current_losses > max_losses:
                max_losses = current_losses
            current_losses = 0
    if current_losses > max_losses:
        max_losses = current_losses
        
    print(f"\nMax Consecutive Losses: {max_losses}")
    
    # Calculate Leverage if risking 10%
    leverages = [10.0 / t["sl_dist_pct"] for t in trades]
    if leverages:
        print(f"\nLeverage Stats (Assuming 10% Risk):")
        print(f"Min Leverage: {min(leverages):.2f}x")
        print(f"Avg Leverage: {sum(leverages)/len(leverages):.2f}x")
        print(f"Max Leverage: {max(leverages):.2f}x")

if __name__ == "__main__":
    run_analysis()
