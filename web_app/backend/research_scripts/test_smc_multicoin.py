from datetime import datetime, timedelta, timezone
import pandas as pd
import numpy as np
import time
from server.main import _fetch_ohlcv_ccxt, _sma, _ema

def test_coin(symbol):
    print(f"Fetching 4 years of 1h data for {symbol}...")
    since = datetime.now(timezone.utc) - timedelta(days=1460)
    try:
        df = _fetch_ohlcv_ccxt("binance", symbol, "1h", since=since, limit=50000)
    except Exception as e:
        print(f"Error fetching {symbol}: {e}")
        return
        
    if len(df) < 1000:
        print(f"Not enough data for {symbol}")
        return
        
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
        dt = pd.to_datetime(df["timestamp"].iloc[i], utc=True)
        
        # Bullish context + Volume boundaries + No Mondays
        if c > e2 and l < lb and (1.5 * v_ma < v < 2.0 * v_ma) and dt.dayofweek != 0:
            candle_range = h - l
            if candle_range > 0:
                close_percent = (c - l) / candle_range
                prev_5_drop = (float(close.iloc[i-5]) - c) / c * 100
                dist_to_e200 = (c - e2) / e2 * 100
                
                # Rejection + No Knife + Not Over-extended
                if close_percent > 0.5 and prev_5_drop < 0.6 and dist_to_e200 < 2.0:
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
                            trades.append(result)
                            i = exit_idx
        i += 1
        
    wins = trades.count("WIN")
    losses = trades.count("LOSS")
    total = len(trades)
    wr = wins / total * 100 if total else 0
    net_r = wins * 2 - losses
    
    print(f"[{symbol}] Trades: {total} | Wins: {wins} | Losses: {losses} | WR: {wr:.2f}% | Net Profit: {net_r:+.2f}R")
    return total, wins, losses, net_r

if __name__ == "__main__":
    coins = ["ETH/USDT", "SOL/USDT", "BNB/USDT", "ADA/USDT", "XRP/USDT"]
    total_t = 0
    total_w = 0
    total_l = 0
    total_r = 0
    
    for coin in coins:
        res = test_coin(coin)
        if res:
            t, w, l, r = res
            total_t += t
            total_w += w
            total_l += l
            total_r += r
        time.sleep(1) # prevent rate limit
        
    overall_wr = total_w / total_t * 100 if total_t else 0
    print("\n" + "="*50)
    print(f"OVERALL SUMMARY (5 Altcoins over 4 Years)")
    print(f"Total Trades: {total_t}")
    print(f"Overall Winrate: {overall_wr:.2f}% (RR = 2.0)")
    print(f"Total Net Profit: {total_r:+.2f}R")
    print("="*50)
