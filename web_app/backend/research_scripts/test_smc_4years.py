from datetime import datetime, timedelta, timezone
import pandas as pd
import numpy as np
from server.main import _fetch_ohlcv_ccxt, _sma, _ema

def test_smc_4years():
    print("Fetching 4 years of 1h data for SMC...")
    since = datetime.now(timezone.utc) - timedelta(days=1460)
    df = _fetch_ohlcv_ccxt("binance", "BTC/USDT", "1h", since=since, limit=50000)
    
    close = df["close"].astype(float)
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    vol = df["volume"].astype(float)
    
    e200 = _ema(close, 200)
    v20 = _sma(vol, 20)
    
    sma20 = _sma(close, 20)
    std20 = close.rolling(20).std()
    lower_band = sma20 - 2 * std20

    trades = []
    i = 205
    
    while i < len(df) - 1:
        c = float(close.iloc[i])
        h = float(high.iloc[i])
        l = float(low.iloc[i])
        v = float(vol.iloc[i])
        v_ma = float(v20.iloc[i]) if pd.notna(v20.iloc[i]) else 0
        e2 = float(e200.iloc[i])
        lb = float(lower_band.iloc[i]) if pd.notna(lower_band.iloc[i]) else 0
        
        # Bullish context
        if c > e2 and l < lb and v > 1.5 * v_ma:
            candle_range = h - l
            if candle_range > 0:
                close_percent = (c - l) / candle_range
                # Rejection
                if close_percent > 0.5:
                    entry = c
                    sl = l - (candle_range * 0.2)
                    risk = abs(entry - sl)
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
                            trades.append({"result": result})
                            i = exit_idx
        i += 1
        
    wins = [t for t in trades if t["result"] == "WIN"]
    losses = [t for t in trades if t["result"] == "LOSS"]
    total = len(trades)
    wr = len(wins) / total * 100 if total else 0
    
    print("\n--- 4-YEAR SMART MONEY (DIP BUY) BACKTEST ---")
    print(f"Total Trades: {total}")
    print(f"Wins: {len(wins)}")
    print(f"Losses: {len(losses)}")
    print(f"Winrate: {wr:.2f}% (RR = 2.0)")

if __name__ == "__main__":
    test_smc_4years()
