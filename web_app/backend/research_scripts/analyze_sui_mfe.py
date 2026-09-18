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

def _supertrend(df: pd.DataFrame, period: int = 10, multiplier: float = 3.0):
    hl2 = (df['high'] + df['low']) / 2
    atr = _atr(df, period)
    basic_ub = hl2 + (multiplier * atr)
    basic_lb = hl2 - (multiplier * atr)
    final_ub = pd.Series(index=df.index, dtype='float64')
    final_lb = pd.Series(index=df.index, dtype='float64')
    trend = pd.Series(index=df.index, dtype='float64')
    final_ub.iloc[0] = basic_ub.iloc[0]
    final_lb.iloc[0] = basic_lb.iloc[0]
    trend.iloc[0] = 1

    for i in range(1, len(df)):
        if pd.isna(basic_ub.iloc[i]):
            final_ub.iloc[i] = np.nan
            final_lb.iloc[i] = np.nan
            trend.iloc[i] = 1
            continue
        if np.isnan(final_ub.iloc[i-1]) or basic_ub.iloc[i] < final_ub.iloc[i-1] or df['close'].iloc[i-1] > final_ub.iloc[i-1]:
            final_ub.iloc[i] = basic_ub.iloc[i]
        else:
            final_ub.iloc[i] = final_ub.iloc[i-1]
        if np.isnan(final_lb.iloc[i-1]) or basic_lb.iloc[i] > final_lb.iloc[i-1] or df['close'].iloc[i-1] < final_lb.iloc[i-1]:
            final_lb.iloc[i] = basic_lb.iloc[i]
        else:
            final_lb.iloc[i] = final_lb.iloc[i-1]
        if trend.iloc[i-1] == 1 and df['close'].iloc[i] < final_lb.iloc[i]:
            trend.iloc[i] = -1
        elif trend.iloc[i-1] == -1 and df['close'].iloc[i] > final_ub.iloc[i]:
            trend.iloc[i] = 1
        else:
            trend.iloc[i] = trend.iloc[i-1]
    return trend

def fetch_data():
    exchange = ccxt.binance({'enableRateLimit': True, 'options': {'defaultType': 'future'}})
    since = exchange.parse8601((datetime.now(timezone.utc) - timedelta(days=700)).isoformat())
    all_data = []
    while True:
        try:
            ohlcv = exchange.fetch_ohlcv("SUI/USDT", '1h', since, 1000)
            if not len(ohlcv): break
            all_data += ohlcv
            since = ohlcv[-1][0] + 3600000 
            if len(ohlcv) < 1000: break
        except Exception as e:
            break
    df = pd.DataFrame(all_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
    df.drop_duplicates(subset='timestamp', inplace=True)
    df.sort_values('timestamp', inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df

def run_analysis():
    df = fetch_data()
    df["st_dir"] = _supertrend(df, 10, 3.0)
    df["e200"] = _ema(df["close"].astype(float), 200)
    df["atr14"] = _atr(df, 14)
    
    setups = []
    i = 205
    while i < len(df) - 1:
        c = df["close"].iloc[i]
        e200 = df["e200"].iloc[i]
        st_dir = df["st_dir"].iloc[i]
        prev_st_dir = df["st_dir"].iloc[i-1]
        at = df["atr14"].iloc[i]
        
        if c > e200 and prev_st_dir == -1 and st_dir == 1:
            setups.append({
                'idx': i,
                'entry': c,
                'atr': at
            })
        i += 1

    sl_mult = 2.0
    mfes = []
    
    for s in setups:
        entry = s['entry']
        sl = entry - sl_mult * s['atr']
        risk = entry - sl
        
        j = s['idx'] + 1
        max_high = entry
        
        while j < len(df):
            hi = df["high"].iloc[j]
            lo = df["low"].iloc[j]
            if hi > max_high:
                max_high = hi
            if lo <= sl: 
                break
            j += 1
            
        mfe_r = (max_high - entry) / risk if risk > 0 else 0
        mfes.append(mfe_r)
        
    print(f"Total SUI Breakouts: {len(mfes)}")
    print(f"Avg MFE: {np.mean(mfes):.2f} R")
    print(f"Median MFE: {np.median(mfes):.2f} R")
    
    r_buckets = {
        '> 15 R': len([x for x in mfes if x >= 15]),
        '> 10 R': len([x for x in mfes if 10 <= x < 15]),
        '>  5 R': len([x for x in mfes if 5 <= x < 10]),
        '>  2 R': len([x for x in mfes if 2 <= x < 5]),
        '<  2 R': len([x for x in mfes if x < 2])
    }
    
    for k, v in r_buckets.items():
        print(f"Reached {k}: {v} trades ({v/len(mfes)*100:.1f}%)")

if __name__ == "__main__":
    run_analysis()
