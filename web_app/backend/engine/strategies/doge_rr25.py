import pandas as pd
from engine.indicators import calculate_ema, calculate_atr, calculate_sma

def check_doge_signal(df: pd.DataFrame):
    """
    Checks the latest closed candle for the DOGE RR 25.0 strategy.
    Returns: 'LONG', 'SHORT', or None
    """
    if len(df) < 205:
        return None
        
    df["e200"] = calculate_ema(df["close"], 200)
    df["e20"] = calculate_ema(df["close"], 20)
    df["v20"] = calculate_sma(df["volume"], 20)
    
    i = len(df) - 2
    
    c = float(df["close"].iloc[i])
    h = float(df["high"].iloc[i])
    l = float(df["low"].iloc[i])
    v = float(df["volume"].iloc[i])
    
    e200_val = float(df["e200"].iloc[i])
    e20_val = float(df["e20"].iloc[i])
    v_ma = float(df["v20"].iloc[i])
    
    last_bullish_cross_idx = 0
    for j in range(i, i - 150, -1):
        if float(df["e20"].iloc[j-1]) <= float(df["e200"].iloc[j-1]) and float(df["e20"].iloc[j]) > float(df["e200"].iloc[j]):
            last_bullish_cross_idx = j
            break
            
    candles_since_cross = i - last_bullish_cross_idx if last_bullish_cross_idx > 0 else 999
    
    candle_range = h - l
    close_pct = (c - l) / candle_range if candle_range > 0 else 0
    candle_size_pct = (candle_range / c) * 100
    dt = pd.to_datetime(df["timestamp"].iloc[i], unit='ms', utc=True)
    dist_to_e200 = ((c - e200_val) / e200_val) * 100
    vol_mult = v / v_ma if v_ma > 0 else 0
    
    # DOGE Rules
    is_uptrend = e20_val > e200_val
    is_proper_speed = 20 <= candles_since_cross < 150
    is_touching = l <= e200_val and c > e200_val
    is_strong_rejection = close_pct > 0.6
    is_proper_session = 8 <= dt.hour <= 18
    is_proper_size = candle_size_pct < 2.5
    is_perfect_touch = dist_to_e200 < 1.0
    is_proper_day = dt.dayofweek not in [5, 6] # No Weekends
    is_proper_vol = 0.5 < vol_mult < 1.8 # Goldilocks volume
    
    if (is_uptrend and is_proper_speed and is_touching and 
        is_strong_rejection and is_proper_session and is_proper_size and 
        is_perfect_touch and is_proper_day and is_proper_vol):
        return "LONG"
        
    return None
