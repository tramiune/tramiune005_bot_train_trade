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

def _sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(window=period).mean()

def run_analysis():
    exchange = ccxt.binance({'enableRateLimit': True, 'options': {'defaultType': 'future'}})
    since = exchange.parse8601((datetime.now(timezone.utc) - timedelta(days=1460)).isoformat())
    
    all_data = []
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
    df["v20"] = _sma(df["volume"].astype(float), 20)
        
    setups = []
    i = 205
    last_bullish_cross_idx = 0
    atr_mult = 1.8
    test_rr = 25.0
    
    while i < len(df) - 1:
        c = float(df["close"].iloc[i])
        h = float(df["high"].iloc[i])
        l = float(df["low"].iloc[i])
        v = float(df["volume"].iloc[i])
        
        e200_val = float(df["e200"].iloc[i]) if pd.notna(df["e200"].iloc[i]) else 0
        e20_val = float(df["e20"].iloc[i]) if pd.notna(df["e20"].iloc[i]) else 0
        prev_e20 = float(df["e20"].iloc[i-1]) if pd.notna(df["e20"].iloc[i-1]) else 0
        prev_e200 = float(df["e200"].iloc[i-1]) if pd.notna(df["e200"].iloc[i-1]) else 0
        at = float(df["atr14"].iloc[i]) if pd.notna(df["atr14"].iloc[i]) else 0
        v_ma = float(df["v20"].iloc[i]) if pd.notna(df["v20"].iloc[i]) else 0
        
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
        
        # CORE FILTERS ALREADY ESTABLISHED
        is_strong_rejection = close_pct > 0.6
        is_proper_session = 8 <= dt.hour <= 18
        is_proper_size = candle_size_pct < 2.5
        is_perfect_touch = dist_to_e200 < 1.0
        
        if is_uptrend and is_proper_speed and is_touching and is_strong_rejection and is_proper_session and is_proper_size and is_perfect_touch:
            entry = c
            sl = entry - atr_mult * at
            risk = entry - sl
            
            if risk > 0:
                tp = entry + test_rr * risk
                j = i + 1
                res = None
                exit_idx = None
                
                while j < len(df):
                    hi = float(df["high"].iloc[j])
                    lo = float(df["low"].iloc[j])
                    if lo <= sl: res = "LOSS"; exit_idx = j; break
                    if hi >= tp: res = "WIN"; exit_idx = j; break
                    j += 1
                    
                if res is not None:
                    setups.append({
                        'idx': i,
                        'exit_idx': exit_idx,
                        'result': res,
                        'date': dt.strftime('%Y-%m-%d %H:%M'),
                        'day': dt.dayofweek,
                        'vol_mult': v / v_ma if v_ma > 0 else 0,
                        'candles_since_cross': candles_since_cross
                    })
                    # Skip overlapping setups
                    i = exit_idx
                    continue
        i += 1
        
    wins = [s for s in setups if s['result'] == 'WIN']
    losses = [s for s in setups if s['result'] == 'LOSS']
    
    print("=== RR 25.0: WINS METADATA (4 Trades) ===")
    for w in wins:
        print(f"[{w['date']}] Day: {w['day']} | Vol: {w['vol_mult']:>4.1f}x | TrendAge: {w['candles_since_cross']:>3}")
        
    print("\n=== RR 25.0: LOSSES METADATA (Sample of 25) ===")
    for l in losses[:25]:
        print(f"[{l['date']}] Day: {l['day']} | Vol: {l['vol_mult']:>4.1f}x | TrendAge: {l['candles_since_cross']:>3}")

if __name__ == "__main__":
    run_analysis()
