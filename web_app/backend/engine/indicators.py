import pandas as pd

def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high = df['high']
    low = df['low']
    close = df['close'].shift(1)
    tr = pd.concat([high - low, (high - close).abs(), (low - close).abs()], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()

def calculate_ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()

def calculate_sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(window=period).mean()

import numpy as np

def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_causal_nadaraya_watson(series: pd.Series, h: float = 8.0, window: int = 100, mult: float = 1.5):
    n = len(series)
    smoothed = np.zeros(n)
    smoothed[:] = np.nan
    i_arr = np.arange(window)
    weights = np.exp(-(i_arr**2) / (2 * h**2))
    sum_weights = np.sum(weights)
    close_vals = series.values
    for t in range(window, n):
        past_closes = close_vals[t-window+1 : t+1][::-1]
        smoothed[t] = np.sum(past_closes * weights) / sum_weights
    
    df_temp = pd.DataFrame({'close': series, 'smoothed': smoothed})
    mae = (df_temp['close'] - df_temp['smoothed']).abs().rolling(window=window).mean()
    lower_band = df_temp['smoothed'] - (mult * mae)
    return lower_band
