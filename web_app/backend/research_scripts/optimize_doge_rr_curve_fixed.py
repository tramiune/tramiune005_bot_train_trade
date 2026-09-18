import ccxt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone

def _atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high = df['high']
    low = df['low']
    close = df['close'].shift(1)
    tr = pd.concat([high - low, (high - close).abs(), (low - close).abs()], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()

def _ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()

def run_analysis():
    exchange = ccxt.binance({'enableRateLimit': True, 'options': {'defaultType': 'future'}})
    since = exchange.parse8601((datetime.now(timezone.utc) - timedelta(days=1460)).isoformat())
    
    all_data = []
    print("Fetching DOGE/USDT data...")
    while True:
        try:
            ohlcv = exchange.fetch_ohlcv("DOGE/USDT", '1h', since, 1000)
            if not len(ohlcv): break
            all_data += ohlcv
            since = ohlcv[-1][0] + 3600000 
            if len(ohlcv) < 1000: break
        except: break
            
    df = pd.DataFrame(all_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
    df.drop_duplicates(subset='timestamp', inplace=True)
    df.sort_values('timestamp', inplace=True)
    df.reset_index(drop=True, inplace=True)
    
    df["e200"] = _ema(df["close"].astype(float), 200)
    df["e20"] = _ema(df["close"].astype(float), 20)
    df["atr14"] = _atr(df, 14)
    
    # Pre-calculate setups (independent of trade execution)
    setups = []
    i = 205
    last_bullish_cross_idx = 0
    atr_mult = 1.8
    
    while i < len(df) - 1:
        c = float(df["close"].iloc[i])
        h = float(df["high"].iloc[i])
        l = float(df["low"].iloc[i])
        
        e200_val = float(df["e200"].iloc[i]) if pd.notna(df["e200"].iloc[i]) else 0
        e20_val = float(df["e20"].iloc[i]) if pd.notna(df["e20"].iloc[i]) else 0
        prev_e20 = float(df["e20"].iloc[i-1]) if pd.notna(df["e20"].iloc[i-1]) else 0
        prev_e200 = float(df["e200"].iloc[i-1]) if pd.notna(df["e200"].iloc[i-1]) else 0
        at = float(df["atr14"].iloc[i]) if pd.notna(df["atr14"].iloc[i]) else 0
        
        if prev_e20 <= prev_e200 and e20_val > e200_val:
            last_bullish_cross_idx = i
            
        candle_range = h - l
        close_pct = (c - l) / candle_range if candle_range > 0 else 0
        candle_size_pct = (candle_range / c) * 100
        dt = pd.to_datetime(df["timestamp"].iloc[i], utc=True)
        dist_to_e200 = ((c - e200_val) / e200_val) * 100
        
        is_uptrend = e20_val > e200_val
        candles_since_cross = i - last_bullish_cross_idx
        is_proper_speed = 20 <= candles_since_cross < 150
        is_touching = l <= e200_val and c > e200_val
        
        is_strong_rejection = close_pct > 0.6
        is_proper_session = 8 <= dt.hour <= 18
        is_proper_size = candle_size_pct < 2.5
        is_perfect_touch = dist_to_e200 < 1.0
        
        if is_uptrend and is_proper_speed and is_touching and is_strong_rejection and is_proper_session and is_proper_size and is_perfect_touch:
            setups.append({
                'idx': i,
                'entry': c,
                'atr': at
            })
        i += 1
        
    print(f"\nFound {len(setups)} raw DOGE God Mode Setups.")
    
    results = []
    # Test fixed RRs. We must simulate trades chronologically to handle overlapping trades correctly!
    for test_rr in [5.0, 10.0, 12.0, 15.0, 18.0, 20.0, 25.0, 30.0]:
        wins = 0
        losses = 0
        i = 0
        while i < len(setups):
            s = setups[i]
            entry = s['entry']
            sl = entry - atr_mult * s['atr']
            risk = entry - sl
            tp = entry + test_rr * risk
            
            j = s['idx'] + 1
            res = None
            exit_idx = None
            while j < len(df):
                hi = float(df["high"].iloc[j])
                lo = float(df["low"].iloc[j])
                if lo <= sl: res = "LOSS"; exit_idx = j; break
                if hi >= tp: res = "WIN"; exit_idx = j; break
                j += 1
                
            if res == "WIN": wins += 1
            elif res == "LOSS": losses += 1
            
            # Skip setups that occur while this trade is open
            next_i = i + 1
            while next_i < len(setups) and setups[next_i]['idx'] <= exit_idx:
                next_i += 1
            i = next_i
            
        tot = wins + losses
        wr = wins / tot * 100 if tot else 0
        net = (wins * test_rr) - losses
        results.append((test_rr, tot, wins, losses, wr, net))
        
    results.sort(key=lambda x: x[5], reverse=True)
    
    print("\n--- RR OPTIMIZATION CURVE FOR DOGE (TOP 8) ---")
    print(f"{'Target RR':<10} | {'Trades':<6} | {'Wins':<5} | {'Losses':<6} | {'WR %':<6} | {'Net R':<6}")
    print("-" * 55)
    for r in results:
        print(f"{r[0]:<10.1f} | {r[1]:<6} | {r[2]:<5} | {r[3]:<6} | {r[4]:<6.1f} | +{r[5]:<5.1f} R")

if __name__ == "__main__":
    run_analysis()
