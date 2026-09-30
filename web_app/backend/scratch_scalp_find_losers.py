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
                        
                        trades.append({
                            "is_win": is_win,
                            "hour": hour,
                            "vol_ratio": vol_ratio,
                            "rsi": rsi_val,
                            "vwap_dist": vwap_dist,
                            "ema200_dist": ema200_dist
                        })
                        i = exit_idx
                    else:
                        i += 1
                    continue
        i += 1
        
    res_df = pd.DataFrame(trades)
    
    print(f"Original Trades: {len(res_df)} (Wins: {res_df['is_win'].sum()}, Losses: {len(res_df)-res_df['is_win'].sum()})")
    
    # Let's find conditions where Losers are concentrated but Winners are NOT.
    print("\n--- ANALYZING LOSERS ---")
    
    # 1. RSI
    print("\nLosses when RSI is HIGH (> 55):")
    high_rsi = res_df[res_df['rsi'] > 55]
    print(f"Trades: {len(high_rsi)}, Wins: {high_rsi['is_win'].sum()}, Losses: {len(high_rsi)-high_rsi['is_win'].sum()}")

    # 2. Distance from EMA200
    print("\nLosses when too far from EMA200 (> 0.5%):")
    far_ema = res_df[res_df['ema200_dist'] > 0.5]
    print(f"Trades: {len(far_ema)}, Wins: {far_ema['is_win'].sum()}, Losses: {len(far_ema)-far_ema['is_win'].sum()}")
    
    # 3. Volume Spike
    print("\nLosses when Volume is LOW (< 0.8x SMA):")
    low_vol = res_df[res_df['vol_ratio'] < 0.8]
    print(f"Trades: {len(low_vol)}, Wins: {low_vol['is_win'].sum()}, Losses: {len(low_vol)-low_vol['is_win'].sum()}")

    print("\n--- OPTIMIZED FILTER TEST ---")
    # Try a filter that drops RSI > 60 and Vol < 0.8
    filtered = res_df[(res_df['rsi'] <= 60) & (res_df['vol_ratio'] >= 0.8)]
    wins = filtered['is_win'].sum()
    losses = len(filtered) - wins
    print(f"New Trades: {len(filtered)} (Wins: {wins}, Losses: {losses})")
    print(f"Win Rate: {wins/len(filtered)*100:.2f}%")
    
asyncio.run(run())
