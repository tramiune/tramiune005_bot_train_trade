import pandas as pd

def check_btc_signal(df: pd.DataFrame) -> str:
    """
    BTC Pullback Strategy RR 1:2
    """
    if len(df) < 201:
        return "NONE"
        
    c = float(df["close"].iloc[-2])
    h = float(df["high"].iloc[-2])
    l = float(df["low"].iloc[-2])
    o = float(df["open"].iloc[-2])
    
    e200 = float(df["e200"].iloc[-2])
    e20 = float(df["e20"].iloc[-2])
    
    candle_range = h - l
    close_pct = (c - l) / candle_range if candle_range > 0 else 0
    candle_size_pct = (abs(c - o) / c) * 100
    
    is_uptrend = e20 > e200
    is_touching = l <= e200 and c > e200
    is_rejection = close_pct > 0.5  # Closed in upper half
    is_proper_size = candle_size_pct < 2.0
    
    hour = pd.to_datetime(df["timestamp"].iloc[-2], unit='ms').hour
    is_ny_session = 12 <= hour <= 18
  # Not a massive anomaly candle
    
    if is_uptrend and is_touching and is_rejection and is_proper_size and is_ny_session:
        return "LONG"
        
    return "NONE"
