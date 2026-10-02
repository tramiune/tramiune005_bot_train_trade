import sys
content = open("backend/server/main.py").read()

new_endpoint = """
@app.get("/api/backtest")
def backtest_general(symbol: str = "BTC/USDT"):
    if symbol == "ETH/USDT":
        # Run ETH VWAP logic and return array of trades
        limit = 50000
        since = datetime.now(timezone.utc) - timedelta(days=limit/(24*12)) 
        df = _fetch_ohlcv_ccxt("binance", symbol, "5m", since=since, limit=limit)
        
        if df.empty: return []

        import numpy as np
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
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')

        trades = []
        i = 288 
        while i < len(df) - 1:
            c = float(df['close'].iloc[i])
            l = float(df['low'].iloc[i])
            h = float(df['high'].iloc[i])
            o = float(df['open'].iloc[i])
            bw = float(df['bandwidth'].iloc[i])
            hour = df['datetime'].iloc[i].hour
            upper = float(df['upper_band'].iloc[i])
            lower = float(df['lower_band'].iloc[i])
            
            is_long = (bw < 5.0) and (hour > 0) and (l <= lower) and (c > lower) and (c > o)
            is_short = (bw < 5.0) and (hour > 0) and (h >= upper) and (c < upper) and (c < o)
            
            if is_long or is_short:
                side = 'LONG' if is_long else 'SHORT'
                entry = c
                sl = entry * (1 - 3.0/100) if side == 'LONG' else entry * (1 + 3.0/100)
                tp = entry * (1 + 2.5/100) if side == 'LONG' else entry * (1 - 2.5/100)
                
                j = i + 1
                exit_idx = None
                
                while j < min(i+288, len(df)):
                    hi = float(df["high"].iloc[j])
                    lo = float(df["low"].iloc[j])
                    if side == 'LONG':
                        if lo <= sl or hi >= tp: 
                            exit_idx = j
                            break
                    else:
                        if hi >= sl or lo <= tp: 
                            exit_idx = j
                            break
                    j += 1
                    
                if exit_idx is not None:
                    exit_ts = int(pd.to_datetime(df["timestamp"].iloc[exit_idx], unit='ms', utc=True).timestamp())
                    entry_ts = int(pd.to_datetime(df["timestamp"].iloc[i], unit='ms', utc=True).timestamp())
                    
                    trades.append({
                        "time": entry_ts,
                        "side": side,
                        "entry": entry,
                        "sl": sl,
                        "tp": tp,
                        "exit_time": exit_ts
                    })
                    i = exit_idx
                    continue
            i += 1
        return trades
    
    return []
"""
if "@app.get(\"/api/backtest\")" not in content:
    open("backend/server/main.py", "a").write("\n" + new_endpoint)
