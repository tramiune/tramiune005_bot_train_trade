import re

with open("backend/server/main.py", "r") as f:
    content = f.read()

new_endpoint = """
@app.get("/api/backtest/eth_vwap")
def backtest_eth_vwap(symbol: str = "ETH/USDT", timeframe: str = "5m", limit: int = 20000):
    since = datetime.now(timezone.utc) - timedelta(days=limit/(24*12)) # Approx days for 5m candles
    df = _fetch_ohlcv_ccxt("binance", symbol, timeframe, since=since, limit=limit)
    
    if df.empty:
        return {"data": [], "markers": [], "metrics": {}}

    import numpy as np
    
    # Calculate VWAP
    df['date'] = df['timestamp'].dt.date if pd.api.types.is_datetime64_any_dtype(df['timestamp']) else pd.to_datetime(df['timestamp'], unit='ms').dt.date
    df['tp'] = (df['high'] + df['low'] + df['close']) / 3
    df['vol_tp'] = df['volume'] * df['tp']
    df['cum_vol'] = df.groupby('date')['volume'].cumsum()
    df['cum_vol_tp'] = df.groupby('date')['vol_tp'].cumsum()
    df['vwap'] = df['cum_vol_tp'] / df['cum_vol']
    df['dev_sq'] = df['volume'] * ((df['tp'] - df['vwap']) ** 2)
    df['cum_dev_sq'] = df.groupby('date')['dev_sq'].cumsum()
    df['variance'] = df['cum_dev_sq'] / df['cum_vol']
    df['sd'] = np.sqrt(df['variance'])
    
    df['upper_band'] = df['vwap'] + (2.5 * df['sd'])
    df['lower_band'] = df['vwap'] - (2.5 * df['sd'])
    df['bandwidth'] = (df['upper_band'] - df['lower_band']) / df['vwap'] * 100
    
    markers = []
    wins = 0
    losses = 0
    
    tp_pct = 2.5
    sl_pct = 3.0
    
    # Ensure datetime for hour check
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')

    i = 288 # Start after 1 day
    while i < len(df) - 1:
        c = float(df['close'].iloc[i])
        l = float(df['low'].iloc[i])
        h = float(df['high'].iloc[i])
        o = float(df['open'].iloc[i])
        
        bw = float(df['bandwidth'].iloc[i])
        hour = df['datetime'].iloc[i].hour
        
        upper = float(df['upper_band'].iloc[i])
        lower = float(df['lower_band'].iloc[i])
        
        dt = pd.to_datetime(df["timestamp"].iloc[i], unit='ms', utc=True)
        ts_ms = int(dt.timestamp() * 1000)
        
        is_long = (bw < 5.0) and (hour > 0) and (l <= lower) and (c > lower) and (c > o)
        is_short = (bw < 5.0) and (hour > 0) and (h >= upper) and (c < upper) and (c < o)
        
        if is_long or is_short:
            side = 'LONG' if is_long else 'SHORT'
            entry = c
            
            if side == 'LONG':
                sl = entry * (1 - sl_pct/100)
                tp = entry * (1 + tp_pct/100)
            else:
                sl = entry * (1 + sl_pct/100)
                tp = entry * (1 - tp_pct/100)
                
            j = i + 1
            exit_idx = None
            result = None
            exit_price = 0
            
            while j < len(df):
                hi = float(df["high"].iloc[j])
                lo = float(df["low"].iloc[j])
                
                if side == 'LONG':
                    if lo <= sl: exit_idx, result, exit_price = j, "LOSS", sl; break
                    if hi >= tp: exit_idx, result, exit_price = j, "WIN", tp; break
                else:
                    if hi >= sl: exit_idx, result, exit_price = j, "LOSS", sl; break
                    if lo <= tp: exit_idx, result, exit_price = j, "WIN", tp; break
                j += 1
                
            if exit_idx is not None:
                exit_ts = int(pd.to_datetime(df["timestamp"].iloc[exit_idx], unit='ms', utc=True).timestamp() * 1000)
                
                # Entry Marker
                markers.append({
                    "time": ts_ms,
                    "position": "belowBar" if side == 'LONG' else "aboveBar",
                    "color": "#9C27B0" if side == 'LONG' else "#E91E63",
                    "shape": "arrowUp" if side == 'LONG' else "arrowDown",
                    "text": f"{side} @ {entry:.2f}"
                })
                
                # Exit Marker
                if result == "WIN":
                    wins += 1
                    markers.append({
                        "time": exit_ts,
                        "position": "aboveBar" if side == 'LONG' else "belowBar",
                        "color": "#4CAF50",
                        "shape": "arrowDown" if side == 'LONG' else "arrowUp",
                        "text": f"TP (+2.5%) @ {exit_price:.2f}"
                    })
                else:
                    losses += 1
                    markers.append({
                        "time": exit_ts,
                        "position": "aboveBar" if side == 'LONG' else "belowBar",
                        "color": "#F44336",
                        "shape": "arrowDown" if side == 'LONG' else "arrowUp",
                        "text": f"SL (-3.0%) @ {exit_price:.2f}"
                    })
                i = exit_idx
                continue
        i += 1
        
    chart_data = []
    for idx, row in df.iterrows():
        chart_data.append({
            "time": int(pd.to_datetime(row["timestamp"], unit='ms', utc=True).timestamp() * 1000),
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"])
        })

    total = wins + losses
    winrate = round(wins / total * 100, 2) if total > 0 else 0
    profit_r = round((wins * 2.5) - (losses * 3.0), 2) # Nominal PnL pct if 100$ used

    return {
        "data": chart_data,
        "markers": markers,
        "metrics": {
            "total_trades": total,
            "wins": wins,
            "losses": losses,
            "winrate": winrate,
            "profit_pct": profit_r
        }
    }
"""

if "/api/backtest/eth_vwap" not in content:
    with open("backend/server/main.py", "a") as f:
        f.write("\n" + new_endpoint)
        print("Endpoint added.")
else:
    print("Endpoint already exists.")
