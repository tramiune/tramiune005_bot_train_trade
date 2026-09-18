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
    df["v20"] = _sma(df["volume"].astype(float), 20)
    
    # Store all breakouts with their metadata
    setups = []
    i = 205
    while i < len(df) - 1:
        c = df["close"].iloc[i]
        v = df["volume"].iloc[i]
        e200 = df["e200"].iloc[i]
        st_dir = df["st_dir"].iloc[i]
        prev_st_dir = df["st_dir"].iloc[i-1]
        at = df["atr14"].iloc[i]
        v20 = df["v20"].iloc[i]
        
        if c > e200 and prev_st_dir == -1 and st_dir == 1:
            dt = pd.to_datetime(df["timestamp"].iloc[i], utc=True)
            setups.append({
                'idx': i,
                'entry': c,
                'atr': at,
                'vol_mult': v / v20 if v20 > 0 else 0,
                'day': dt.dayofweek,
                'hour': dt.hour
            })
        i += 1

    sl_mult = 2.0
    rr = 15.0
    
    print("--- SUI FILTER OPTIMIZATION (SL 2.0 ATR, RR 15.0) ---")
    
    # Apply Volume Filter
    for vol_threshold in [1.0, 1.2, 1.5, 2.0]:
        filtered_setups = [s for s in setups if s['vol_mult'] > vol_threshold]
        
        wins, losses = 0, 0
        for s in filtered_setups:
            entry = s['entry']
            sl = entry - sl_mult * s['atr']
            risk = entry - sl
            tp = entry + rr * risk
            
            j = s['idx'] + 1
            res = None
            while j < len(df):
                hi = df["high"].iloc[j]
                lo = df["low"].iloc[j]
                if lo <= sl: res = "LOSS"; break
                if hi >= tp: res = "WIN"; break
                j += 1
            if res == "WIN": wins += 1
            elif res == "LOSS": losses += 1
            
        tot = wins + losses
        wr = wins/tot*100 if tot else 0
        net_r = (wins * rr) - (losses * 1.0)
        print(f"Vol > {vol_threshold:.1f}x | Trades: {tot:>3} | W: {wins:>2} | L: {losses:>3} | WR: {wr:>4.1f}% | Net: {net_r:>+5.1f}R")

if __name__ == "__main__":
    run_analysis()
