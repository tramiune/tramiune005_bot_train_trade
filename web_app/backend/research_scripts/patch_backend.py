import re

with open("server/main.py", "r") as f:
    content = f.read()

new_endpoint = """
@app.get("/api/backtest/eth_squeeze")
def backtest_eth_squeeze(symbol: str = "ETH/USDT", timeframe: str = "1h", limit: int = 50000, rr: float = 5.0):
    since = datetime.now(timezone.utc) - timedelta(days=limit)
    df = _fetch_ohlcv_ccxt("binance", symbol, timeframe, since=since, limit=100000)
    if df.empty:
        return {"data": [], "markers": [], "metrics": {}}

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

    markers = []
    i = 205
    wins = 0
    losses = 0

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
        ts_ms = int(dt.timestamp() * 1000)

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
                exit_price = 0

                while j < len(df):
                    hi = float(high.iloc[j])
                    lo = float(low.iloc[j])
                    if lo <= sl: 
                        exit_idx, result, exit_price = j, "LOSS", sl
                        break
                    if hi >= tp: 
                        exit_idx, result, exit_price = j, "WIN", tp
                        break
                    j += 1

                if exit_idx is not None:
                    exit_ts = int(pd.to_datetime(df["timestamp"].iloc[exit_idx], utc=True).timestamp() * 1000)
                    markers.append({
                        "time": ts_ms,
                        "position": "belowBar",
                        "color": "#2196F3",
                        "shape": "arrowUp",
                        "text": f"BUY @ {entry:.2f}"
                    })
                    if result == "WIN":
                        wins += 1
                        markers.append({
                            "time": exit_ts,
                            "position": "aboveBar",
                            "color": "#4CAF50",
                            "shape": "arrowDown",
                            "text": f"TP (+{rr}R) @ {exit_price:.2f}"
                        })
                    else:
                        losses += 1
                        markers.append({
                            "time": exit_ts,
                            "position": "aboveBar",
                            "color": "#F44336",
                            "shape": "arrowDown",
                            "text": f"SL (-1R) @ {exit_price:.2f}"
                        })
                    i = exit_idx
        i += 1

    chart_data = []
    for idx, row in df.iterrows():
        chart_data.append({
            "time": int(pd.to_datetime(row["timestamp"], utc=True).timestamp() * 1000),
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"])
        })

    total = wins + losses
    winrate = round(wins / total * 100, 2) if total > 0 else 0
    profit_r = round((wins * rr) - (losses * 1.0), 2)

    return {
        "data": chart_data,
        "markers": markers,
        "metrics": {
            "total_trades": total,
            "wins": wins,
            "losses": losses,
            "winrate": winrate,
            "profit_r": profit_r
        }
    }
"""

if "def backtest_eth_squeeze" not in content:
    content += "\n" + new_endpoint
    with open("server/main.py", "w") as f:
        f.write(content)
