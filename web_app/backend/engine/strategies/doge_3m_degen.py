import pandas as pd
import numpy as np

def check_doge_degen_signal(df: pd.DataFrame) -> str:
    if len(df) < 50:
        return None
        
    period = 20
    
    # Calculate TR and ATR
    df['tr'] = np.maximum(
        df['high'] - df['low'],
        np.maximum(abs(df['high'] - df['close'].shift()), abs(df['low'] - df['close'].shift()))
    )
    df['atr'] = df['tr'].rolling(window=period).mean()
    
    # Calculate KC
    df['kc_mid'] = df['close'].rolling(window=period).mean()
    df['kc_upper'] = df['kc_mid'] + (1.5 * df['atr'])
    df['kc_lower'] = df['kc_mid'] - (1.5 * df['atr'])
    
    # Calculate BB
    df['bb_mid'] = df['close'].rolling(window=period).mean()
    df['bb_std'] = df['close'].rolling(window=period).std()
    df['bb_upper'] = df['bb_mid'] + (2.0 * df['bb_std'])
    df['bb_lower'] = df['bb_mid'] - (2.0 * df['bb_std'])
    
    # Calculate Vol MA
    df['vol_ma'] = df['volume'].rolling(window=20).mean()
    
    # Squeeze logic
    df['squeeze_on'] = (df['bb_upper'] < df['kc_upper']) & (df['bb_lower'] > df['kc_lower'])
    df['squeeze_off'] = ~df['squeeze_on']
    df['squeeze_duration'] = df['squeeze_on'].groupby((~df['squeeze_on']).cumsum()).cumsum()
    
    # Live signal check (we look at index -2 because index -1 is the currently forming candle)
    i = len(df) - 2
    
    was_squeezed = df['squeeze_duration'].iloc[i-1] >= 5
    fires_now = df['squeeze_off'].iloc[i] and df['squeeze_on'].iloc[i-1]
    high_vol = df['volume'].iloc[i] > (1.5 * df['vol_ma'].iloc[i])
    
    if was_squeezed and fires_now and high_vol:
        is_bullish_breakout = df['close'].iloc[i] > df['bb_mid'].iloc[i]
        return 'SHORT' if is_bullish_breakout else 'LONG'
        
    return None


def get_all_doge_degen_signals(df: pd.DataFrame):
    signals = []
    if len(df) < 50:
        return signals
        
    period = 20
    df['tr'] = np.maximum(
        df['high'] - df['low'],
        np.maximum(abs(df['high'] - df['close'].shift()), abs(df['low'] - df['close'].shift()))
    )
    df['atr'] = df['tr'].rolling(window=period).mean()
    df['kc_mid'] = df['close'].rolling(window=period).mean()
    df['kc_upper'] = df['kc_mid'] + (1.5 * df['atr'])
    df['kc_lower'] = df['kc_mid'] - (1.5 * df['atr'])
    
    df['bb_mid'] = df['close'].rolling(window=period).mean()
    df['bb_std'] = df['close'].rolling(window=period).std()
    df['bb_upper'] = df['bb_mid'] + (2.0 * df['bb_std'])
    df['bb_lower'] = df['bb_mid'] - (2.0 * df['bb_std'])
    
    df['vol_ma'] = df['volume'].rolling(window=20).mean()
    
    df['squeeze_on'] = (df['bb_upper'] < df['kc_upper']) & (df['bb_lower'] > df['kc_lower'])
    df['squeeze_off'] = ~df['squeeze_on']
    df['squeeze_duration'] = df['squeeze_on'].groupby((~df['squeeze_on']).cumsum()).cumsum()
    
    for i in range(200, len(df)):
        was_squeezed = df['squeeze_duration'].iloc[i-1] >= 5
        fires_now = df['squeeze_off'].iloc[i] and df['squeeze_on'].iloc[i-1]
        high_vol = df['volume'].iloc[i] > (1.5 * df['vol_ma'].iloc[i])
        
        if was_squeezed and fires_now and high_vol:
            is_bullish_breakout = df['close'].iloc[i] > df['bb_mid'].iloc[i]
            side = 'SHORT' if is_bullish_breakout else 'LONG'
            signals.append({
                'time': df['timestamp'].iloc[i],
                'side': side,
                'entry_price': df['close'].iloc[i]
            })
            
    return signals
