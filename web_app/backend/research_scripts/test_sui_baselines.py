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

def fetch_data(symbol, days=700):
    exchange = ccxt.binance({'enableRateLimit': True, 'options': {'defaultType': 'future'}})
    since = exchange.parse8601((datetime.now(timezone.utc) - timedelta(days=days)).isoformat())
    all_data = []
    while True:
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, '1h', since, 1000)
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

def run_test():
    df = fetch_data("SUI/USDT")
    df["st_dir"] = _supertrend(df, 10, 3.0)
    df["e200"] = _ema(df["close"].astype(float), 200)
    
    trades = []
    i = 205
    while i < len(df) - 1:
        c = df["close"].iloc[i]
        e200 = df["e200"].iloc[i]
        st_dir = df["st_dir"].iloc[i]
        prev_st_dir = df["st_dir"].iloc[i-1]
        
        if c > e200 and prev_st_dir == -1 and st_dir == 1:
            entry = c
            j = i + 1
            exit_idx = None
            res = None
            while j < len(df):
                if df["st_dir"].iloc[j] == -1:
                    exit_price = df["close"].iloc[j]
                    res = exit_price - entry
                    exit_idx = j
                    break
                j += 1
            if exit_idx:
                trades.append(res)
                i = exit_idx
                continue
        i += 1
        
    wins = len([t for t in trades if t > 0])
    losses = len([t for t in trades if t <= 0])
    tot = len(trades)
    wr = wins / tot * 100 if tot else 0
    print(f"SUI Supertrend (10, 3.0) Breakout Baseline: Trades={tot}, Wins={wins}, Losses={losses}, WR={wr:.1f}%")

if __name__ == "__main__":
    run_test()
