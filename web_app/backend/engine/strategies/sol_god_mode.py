import pandas as pd
from engine.indicators import calculate_ema, calculate_atr, calculate_sma

def check_sol_signal(df: pd.DataFrame, btc_df: pd.DataFrame):
    """
    Checks the latest closed candle for the SOL God Mode RR15 strategy.
    Returns: 'LONG', 'SHORT', or None
    """
    if len(df) < 205 or len(btc_df) < 205:
        return None
        
    df["e200"] = calculate_ema(df["close"], 200)
    df["e20"] = calculate_ema(df["close"], 20)
    df["v20"] = calculate_sma(df["volume"], 20)
    btc_df["btc_e200"] = calculate_ema(btc_df["close"], 200)
    
    # Merge BTC e200 to main df
    df = pd.merge(df, btc_df[['timestamp', 'btc_e200']], on='timestamp', how='left')
    
    # Get the latest completed candle (idx -2 because -1 is currently forming)
    i = len(df) - 2
    
    c = float(df["close"].iloc[i])
    h = float(df["high"].iloc[i])
    l = float(df["low"].iloc[i])
    v = float(df["volume"].iloc[i])
    
    e200_val = float(df["e200"].iloc[i])
    e20_val = float(df["e20"].iloc[i])
    v_ma = float(df["v20"].iloc[i])
    btc_e200_val = float(df["btc_e200"].iloc[i])
    btc_c = float(btc_df["close"].iloc[i])
    
    # Find last cross
    last_bullish_cross_idx = 0
    for j in range(i, i - 150, -1):
        if float(df["e20"].iloc[j-1]) <= float(df["e200"].iloc[j-1]) and float(df["e20"].iloc[j]) > float(df["e200"].iloc[j]):
            last_bullish_cross_idx = j
            break
            
    candles_since_cross = i - last_bullish_cross_idx if last_bullish_cross_idx > 0 else 999
    
    candle_range = h - l
    close_pct = (c - l) / candle_range if candle_range > 0 else 0
    candle_size_pct = (abs(c - float(df["open"].iloc[i])) / c) * 100
    dt = pd.to_datetime(df["timestamp"].iloc[i], unit='ms', utc=True)
    
    # Strategy Rules
    is_uptrend = e20_val > e200_val
    btc_uptrend = btc_c > btc_e200_val
    is_proper_speed = 20 <= candles_since_cross < 150
    is_touching = l <= e200_val and c > e200_val
    is_strong_rejection = close_pct > 0.6
    is_proper_session = 8 <= dt.hour <= 18
    is_proper_size = candle_size_pct < 2.5
    is_proper_volume = v > 1.2 * v_ma
    is_proper_day = dt.dayofweek in [1, 2, 3] # Tue, Wed, Thu
    
    if (is_uptrend and btc_uptrend and is_proper_speed and is_touching and 
        is_strong_rejection and is_proper_session and is_proper_size and 
        is_proper_volume and is_proper_day):
        return "LONG"
        
    return None
