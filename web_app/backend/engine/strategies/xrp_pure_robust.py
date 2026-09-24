import pandas as pd
from engine.indicators import calculate_causal_nadaraya_watson, calculate_rsi, calculate_sma, calculate_ema

def check_xrp_signal(df: pd.DataFrame, btc_df: pd.DataFrame) -> str:
    """
    XRP 5m Pure Robust Strategy.
    Mean Reversion using Causal Nadaraya-Watson Envelope.
    RR 1:2 (TP: 1.5%, SL: 3.0%). Fixed Risk.
    """
    if len(df) < 150 or len(btc_df) < 205:
        return "NONE"
        
    # Calculate Indicators
    df['nada_low'] = calculate_causal_nadaraya_watson(df['close'], h=8, window=100, mult=1.5)
    df['rsi'] = calculate_rsi(df['close'], period=14)
    df['v20'] = calculate_sma(df['volume'], period=20)
    
    btc_df['btc_e200'] = calculate_ema(btc_df['close'], period=200)
    
    # Merge BTC to check macro trend
    df = pd.merge(df, btc_df[['timestamp', 'btc_e200']], on='timestamp', how='left')
    
    # Check latest completed candle
    i = len(df) - 2
    
    if i < 100:
        return "NONE"
        
    c = float(df['close'].iloc[i])
    l = float(df['low'].iloc[i])
    v = float(df['volume'].iloc[i])
    
    nada_low_val = float(df['nada_low'].iloc[i])
    rsi_val = float(df['rsi'].iloc[i])
    v_ma = float(df['v20'].iloc[i])
    btc_e200_val = float(df['btc_e200'].iloc[i])
    btc_c = float(btc_df['close'].iloc[-2]) # Latest closed BTC candle
    
    # Pure Robust Conditions
    is_extreme_drop = (l <= nada_low_val) and (c > nada_low_val)
    is_oversold = rsi_val < 40.0
    is_high_volume = v > (1.0 * v_ma) if v_ma > 0 else False
    is_btc_bullish = btc_c > btc_e200_val
    
    if is_extreme_drop and is_oversold and is_high_volume and is_btc_bullish:
        return "LONG"
        
    return "NONE"
