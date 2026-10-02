import pandas as pd
from engine.indicators import calculate_ema, calculate_sma, calculate_atr

def backtest_doge_rr25(df: pd.DataFrame):
    df["e200"] = calculate_ema(df["close"], 200)
    df["e20"] = calculate_ema(df["close"], 20)
    df["v20"] = calculate_sma(df["volume"], 20)
    df["atr14"] = calculate_atr(df, 14)
    
    trades = []
    
    i = 205
    while i < len(df) - 1:
        c = float(df["close"].iloc[i])
        h = float(df["high"].iloc[i])
        l = float(df["low"].iloc[i])
        o = float(df["open"].iloc[i])
        v = float(df["volume"].iloc[i])
        
        e200_val = float(df["e200"].iloc[i])
        e20_val = float(df["e20"].iloc[i])
        v_ma = float(df["v20"].iloc[i])
        atr = float(df["atr14"].iloc[i])
        
        last_bullish_cross_idx = 0
        for j in range(i, max(0, i - 150), -1):
            if float(df["e20"].iloc[j-1]) <= float(df["e200"].iloc[j-1]) and float(df["e20"].iloc[j]) > float(df["e200"].iloc[j]):
                last_bullish_cross_idx = j
                break
                
        candles_since_cross = i - last_bullish_cross_idx if last_bullish_cross_idx > 0 else 999
        
        candle_range = h - l
        close_pct = (c - l) / candle_range if candle_range > 0 else 0
        candle_size_pct = (abs(c - o) / c) * 100
        dt = pd.to_datetime(df["timestamp"].iloc[i], unit='ms', utc=True)
        dist_to_e200 = ((c - e200_val) / e200_val) * 100
        vol_mult = v / v_ma if v_ma > 0 else 0
        
        is_uptrend = e20_val > e200_val
        is_proper_speed = 20 <= candles_since_cross < 150
        is_touching = l <= e200_val and c > e200_val
        is_strong_rejection = close_pct > 0.6
        is_proper_session = 8 <= dt.hour <= 18
        is_proper_size = candle_size_pct < 2.5
        is_perfect_touch = dist_to_e200 < 1.0
        is_proper_day = dt.dayofweek not in [5, 6]
        is_proper_vol = 0.5 < vol_mult < 1.8
        
        if (is_uptrend and is_proper_speed and is_touching and 
            is_strong_rejection and is_proper_session and is_proper_size and 
            is_perfect_touch and is_proper_day and is_proper_vol):
            
            sl = c - (1.8 * atr)
            tp = c + (25.0 * (c - sl))
            
            # Forward i to the exit candle
            j = i + 1
            exit_idx = None
            while j < len(df):
                hi = float(df["high"].iloc[j])
                lo = float(df["low"].iloc[j])
                if lo <= sl: exit_idx = j; break
                if hi >= tp: exit_idx = j; break
                j += 1
                
            exit_time = float(df["timestamp"].iloc[exit_idx]) / 1000 if exit_idx else float(df["timestamp"].iloc[-1]) / 1000
            
            trades.append({
                "time": float(df["timestamp"].iloc[i]) / 1000,
                "exit_time": exit_time,
                "side": "LONG",
                "entry": c,
                "sl": sl,
                "tp": tp
            })
            
            if exit_idx is not None:
                i = exit_idx
                continue
                
        i += 1
            
    return trades

def backtest_sol_god_mode(df: pd.DataFrame, btc_df: pd.DataFrame):
    df["e200"] = calculate_ema(df["close"], 200)
    df["e20"] = calculate_ema(df["close"], 20)
    df["v20"] = calculate_sma(df["volume"], 20)
    df["atr14"] = calculate_atr(df, 14)
    btc_df["btc_e200"] = calculate_ema(btc_df["close"], 200)
    
    df = pd.merge(df, btc_df[['timestamp', 'btc_e200']], on='timestamp', how='left')
    
    trades = []
    
    i = 205
    while i < len(df) - 1:
        c = float(df["close"].iloc[i])
        h = float(df["high"].iloc[i])
        l = float(df["low"].iloc[i])
        o = float(df["open"].iloc[i])
        v = float(df["volume"].iloc[i])
        
        e200_val = float(df["e200"].iloc[i])
        e20_val = float(df["e20"].iloc[i])
        v_ma = float(df["v20"].iloc[i])
        btc_e200_val = float(df["btc_e200"].iloc[i])
        btc_c = float(btc_df["close"].iloc[i])
        atr = float(df["atr14"].iloc[i])
        
        last_bullish_cross_idx = 0
        for j in range(i, max(0, i - 150), -1):
            if float(df["e20"].iloc[j-1]) <= float(df["e200"].iloc[j-1]) and float(df["e20"].iloc[j]) > float(df["e200"].iloc[j]):
                last_bullish_cross_idx = j
                break
                
        candles_since_cross = i - last_bullish_cross_idx if last_bullish_cross_idx > 0 else 999
        
        candle_range = h - l
        close_pct = (c - l) / candle_range if candle_range > 0 else 0
        candle_size_pct = (abs(c - o) / c) * 100
        dt = pd.to_datetime(df["timestamp"].iloc[i], unit='ms', utc=True)
        
        is_uptrend = e20_val > e200_val
        btc_uptrend = btc_c > btc_e200_val
        is_proper_speed = 20 <= candles_since_cross < 150
        is_touching = l <= e200_val and c > e200_val
        is_strong_rejection = close_pct > 0.6
        is_proper_session = 8 <= dt.hour <= 18
        is_proper_size = candle_size_pct < 2.5
        is_proper_volume = v > 1.2 * v_ma
        is_proper_day = dt.dayofweek in [1, 2, 3]
        
        if (is_uptrend and btc_uptrend and is_proper_speed and is_touching and 
            is_strong_rejection and is_proper_session and is_proper_size and 
            is_proper_volume and is_proper_day):
            
            sl = c - (1.8 * atr)
            tp = c + (15.0 * (c - sl))
            
            # Forward i to the exit candle
            j = i + 1
            exit_idx = None
            while j < len(df):
                hi = float(df["high"].iloc[j])
                lo = float(df["low"].iloc[j])
                if lo <= sl: exit_idx = j; break
                if hi >= tp: exit_idx = j; break
                j += 1
                
            exit_time = float(df["timestamp"].iloc[exit_idx]) / 1000 if exit_idx else float(df["timestamp"].iloc[-1]) / 1000
            
            trades.append({
                "time": float(df["timestamp"].iloc[i]) / 1000,
                "exit_time": exit_time,
                "side": "LONG",
                "entry": c,
                "sl": sl,
                "tp": tp
            })
            
            if exit_idx is not None:
                i = exit_idx
                continue
                
        i += 1
            
    return trades

def backtest_btc_rr2(df: pd.DataFrame):
    df["e20"] = df["close"].ewm(span=20, adjust=False).mean()
    df["e200"] = df["close"].ewm(span=200, adjust=False).mean()
    
    trades = []
    i = 200
    while i < len(df) - 1:
        c = float(df["close"].iloc[i])
        h = float(df["high"].iloc[i])
        l = float(df["low"].iloc[i])
        o = float(df["open"].iloc[i])
        
        e200 = float(df["e200"].iloc[i])
        e20 = float(df["e20"].iloc[i])
        
        candle_range = h - l
        close_pct = (c - l) / candle_range if candle_range > 0 else 0
        candle_size_pct = (abs(c - o) / c) * 100
        
        is_uptrend = e20 > e200
        is_touching = l <= e200 and c > e200
        is_rejection = close_pct > 0.5
        is_proper_size = candle_size_pct < 2.0
        
        hour = pd.to_datetime(df["timestamp"].iloc[i], unit='ms').hour
        is_ny_session = 12 <= hour <= 18

        
        if is_uptrend and is_touching and is_rejection and is_proper_size and is_ny_session:
            entry_price = float(df["close"].iloc[i])
            sl = entry_price - (2.5 * float(df["atr14"].iloc[i]))
            # Risk:Reward 1:2
            tp = entry_price + (2.0 * (entry_price - sl))
            
            exit_time = None
            exit_idx = i
            for j in range(i + 1, len(df)):
                curr_h = float(df["high"].iloc[j])
                curr_l = float(df["low"].iloc[j])
                if curr_l <= sl:
                    exit_time = df["timestamp"].iloc[j] / 1000
                    exit_idx = j
                    break
                if curr_h >= tp:
                    exit_time = df["timestamp"].iloc[j] / 1000
                    exit_idx = j
                    break
                    
            trades.append({
                "time": df["timestamp"].iloc[i] / 1000,
                "side": "LONG",
                "entry": entry_price,
                "sl": sl,
                "tp": tp,
                "exit_time": exit_time
            })
            if exit_idx > i:
                i = exit_idx
            else:
                i += 1
        else:
            i += 1
            
    return trades

import numpy as np

def backtest_doge_3m_degen(df):
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
    
    trades = []
    tp_pct = 5.0
    sl_pct = 15.0
    
    i = 200
    while i < len(df) - 1:
        was_squeezed = df['squeeze_duration'].iloc[i-1] >= 5
        fires_now = df['squeeze_off'].iloc[i] and df['squeeze_on'].iloc[i-1]
        high_vol = df['volume'].iloc[i] > (1.5 * df['vol_ma'].iloc[i])
        
        if was_squeezed and fires_now and high_vol:
            is_bullish_breakout = df['close'].iloc[i] > df['bb_mid'].iloc[i]
            side = 'SHORT' if is_bullish_breakout else 'LONG'
            entry = df['close'].iloc[i]
            
            if side == 'LONG':
                sl_price = entry * (1 - sl_pct/100)
                tp_price = entry * (1 + tp_pct/100)
            else:
                sl_price = entry * (1 + sl_pct/100)
                tp_price = entry * (1 - tp_pct/100)
                
            exit_idx = i
            exit_price = 0
            is_win = False
            for j in range(i+1, min(i+1440, len(df))):
                if side == 'LONG':
                    if df['low'].iloc[j] <= sl_price:
                        is_win = False; exit_idx = j; exit_price = sl_price; break
                    elif df['high'].iloc[j] >= tp_price:
                        is_win = True; exit_idx = j; exit_price = tp_price; break
                else:
                    if df['high'].iloc[j] >= sl_price:
                        is_win = False; exit_idx = j; exit_price = sl_price; break
                    elif df['low'].iloc[j] <= tp_price:
                        is_win = True; exit_idx = j; exit_price = tp_price; break
            
            if exit_idx > i:
                trades.append({
                    "side": side,
                    "entry": float(entry),
                    "exit_price": float(exit_price),
                    "time": df['timestamp'].iloc[i] / 1000 if df['timestamp'].iloc[i] > 2000000000 else df['timestamp'].iloc[i],
                    "exit_time": df['timestamp'].iloc[exit_idx] / 1000 if df['timestamp'].iloc[exit_idx] > 2000000000 else df['timestamp'].iloc[exit_idx],
                    "tp": tp_price,
                    "sl": sl_price,
                    "pnl": 1 if is_win else -1
                })
                i = exit_idx
                continue
        i += 1
    return trades
