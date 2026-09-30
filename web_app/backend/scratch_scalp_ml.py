import asyncio
import pandas as pd
import numpy as np
from engine.exchange import BinanceFutures

def calculate_vwap(df):
    q = df['volume'] * ((df['high'] + df['low'] + df['close']) / 3)
    return q.rolling(window=1440).sum() / df['volume'].rolling(window=1440).sum()

def calculate_rsi(df, period=14):
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

async def run():
    ex = BinanceFutures()
    from fetch_more import fetch_lots_of_klines
    data = await fetch_lots_of_klines(ex.exchange, "SOL/USDT", "1m", 20000)
    df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    
    df['ema9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['ema200'] = df['close'].ewm(span=200, adjust=False).mean()
    df['vwap'] = calculate_vwap(df)
    df['rsi'] = calculate_rsi(df, 14)
    df['vol_sma20'] = df['volume'].rolling(20).mean()
    
    tp_pct = 1.5
    sl_pct = 0.7
    trades = []
    
    i = 1500
    while i < len(df) - 1:
        if df['close'].iloc[i] > df['vwap'].iloc[i]:
            if df['ema9'].iloc[i] > df['ema21'].iloc[i]:
                if df['low'].iloc[i] <= df['ema21'].iloc[i] and df['close'].iloc[i] > df['ema21'].iloc[i]:
                    entry_price = df['close'].iloc[i]
                    sl = entry_price * (1 - sl_pct/100)
                    tp = entry_price * (1 + tp_pct/100)
                    
                    is_win = False
                    exit_idx = i
                    for j in range(i+1, min(i+1440, len(df))):
                        if df['low'].iloc[j] <= sl:
                            is_win = False
                            exit_idx = j
                            break
                        elif df['high'].iloc[j] >= tp:
                            is_win = True
                            exit_idx = j
                            break
                            
                    if exit_idx > i:
                        hour = pd.to_datetime(df["timestamp"].iloc[i], unit='ms').hour
                        vol_ratio = df["volume"].iloc[i] / df["vol_sma20"].iloc[i] if df["vol_sma20"].iloc[i] > 0 else 1
                        rsi_val = df["rsi"].iloc[i]
                        vwap_dist = ((entry_price - df["vwap"].iloc[i]) / df["vwap"].iloc[i]) * 100
                        ema200_dist = ((entry_price - df["ema200"].iloc[i]) / df["ema200"].iloc[i]) * 100
                        candle_size = (df['high'].iloc[i] - df['low'].iloc[i]) / df['open'].iloc[i] * 100
                        
                        trades.append({
                            "is_win": is_win,
                            "hour": hour,
                            "vol_ratio": vol_ratio,
                            "rsi": rsi_val,
                            "vwap_dist": vwap_dist,
                            "ema200_dist": ema200_dist,
                            "candle_size": candle_size
                        })
                        i = exit_idx
                    else:
                        i += 1
                    continue
        i += 1
        
    res_df = pd.DataFrame(trades)
    
    # Brute force search for the best filter
    best_filter = None
    best_wins = 0
    best_losses = 999
    best_score = -999 # Score = Wins - Losses
    
    for rsi_max in [45, 50, 55, 60, 65, 70, 80, 100]:
        for rsi_min in [0, 20, 30, 40, 50]:
            for vol_min in [0, 0.5, 0.8, 1.0, 1.2]:
                for vwap_min in [0, 0.2, 0.4, 0.6, 0.8]:
                    for candle_max in [0.2, 0.3, 0.5, 1.0, 2.0]:
                        
                        f = res_df[
                            (res_df['rsi'] <= rsi_max) & 
                            (res_df['rsi'] >= rsi_min) & 
                            (res_df['vol_ratio'] >= vol_min) & 
                            (res_df['vwap_dist'] >= vwap_min) &
                            (res_df['candle_size'] <= candle_max)
                        ]
                        
                        if len(f) < 10:
                            continue
                            
                        w = f['is_win'].sum()
                        l = len(f) - w
                        
                        # We want high win rate and high total wins
                        score = w - (l * 1.5) # Penalize losses heavily
                        
                        if score > best_score:
                            best_score = score
                            best_wins = w
                            best_losses = l
                            best_filter = f"RSI: {rsi_min}-{rsi_max} | Vol > {vol_min} | VWAP dist > {vwap_min} | Candle < {candle_max}%"
                            
    print("=== BEST BRUTE FORCE FILTER ===")
    print(best_filter)
    print(f"Filtered Trades: {best_wins + best_losses} (Wins: {best_wins}, Losses: {best_losses})")
    print(f"Win Rate: {best_wins/(best_wins+best_losses)*100:.2f}%")
    
asyncio.run(run())
