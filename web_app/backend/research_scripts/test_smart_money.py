from datetime import datetime, timedelta, timezone
import pandas as pd
import numpy as np
from server.main import _fetch_ohlcv_ccxt, _sma, _ema

def test_vpa():
    print("Fetching 180 days of 1h data...")
    since = datetime.now(timezone.utc) - timedelta(days=180)
    df = _fetch_ohlcv_ccxt("binance", "BTC/USDT", "1h", since=since, limit=50000)
    print(f"Loaded {len(df)} 1h candles.")

    close = df["close"].astype(float)
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    open_ = df["open"].astype(float)
    vol = df["volume"].astype(float)
    
    e200 = _ema(close, 200)
    v20 = _sma(vol, 20)
    
    # Bollinger Bands for detecting dips
    sma20 = _sma(close, 20)
    std20 = close.rolling(20).std()
    lower_band = sma20 - 2 * std20

    trades = []
    i = 205
    
    while i < len(df) - 1:
        c = float(close.iloc[i])
        o = float(open_.iloc[i])
        h = float(high.iloc[i])
        l = float(low.iloc[i])
        v = float(vol.iloc[i])
        v_ma = float(v20.iloc[i]) if pd.notna(v20.iloc[i]) else 0
        e2 = float(e200.iloc[i])
        lb = float(lower_band.iloc[i])
        
        # Trend is up
        if c > e2:
            # Reached support/dip (Low pierced lower bollinger band)
            if l < lb:
                # Volume anomaly (smart money stepping in)
                if v > 1.5 * v_ma:
                    # Price Action: Rejection (Pinbar or closing in upper half of the candle's range)
                    candle_range = h - l
                    if candle_range > 0:
                        close_percent = (c - l) / candle_range
                        if close_percent > 0.5: # Closed in top 50% (absorbed selling pressure)
                            
                            entry = c
                            sl = l - (candle_range * 0.2) # SL slightly below the wick
                            risk = entry - sl
                            if risk > 0:
                                rr = 2.0
                                tp = entry + rr * risk
                                
                                j = i + 1
                                exit_idx = None
                                result = None
                                
                                while j < len(df):
                                    hi = float(high.iloc[j])
                                    lo = float(low.iloc[j])
                                    if lo <= sl: exit_idx, result = j, "LOSS"; break
                                    if hi >= tp: exit_idx, result = j, "WIN"; break
                                    j += 1
                                    
                                if exit_idx is not None:
                                    trades.append({"entry": entry, "result": result, "risk": risk, "sl": sl})
                                    i = exit_idx
        i += 1
        
    wins = [t for t in trades if t["result"] == "WIN"]
    losses = [t for t in trades if t["result"] == "LOSS"]
    total = len(trades)
    wr = len(wins) / total * 100 if total else 0
    
    print("\n--- SMART MONEY VPA BACKTEST ---")
    print(f"Total Trades: {total}")
    print(f"Wins: {len(wins)}, Losses: {len(losses)}")
    print(f"Winrate: {wr:.2f}% (RR = 2.0)")

if __name__ == "__main__":
    test_vpa()
