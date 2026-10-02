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
                        # Extract features
                        hour = pd.to_datetime(df["timestamp"].iloc[i], unit='ms').hour
                        dow = pd.to_datetime(df["timestamp"].iloc[i], unit='ms').dayofweek
                        vol_ratio = df["volume"].iloc[i] / df["vol_sma20"].iloc[i] if df["vol_sma20"].iloc[i] > 0 else 1
                        rsi_val = df["rsi"].iloc[i]
                        vwap_dist = ((entry_price - df["vwap"].iloc[i]) / df["vwap"].iloc[i]) * 100
                        
                        trades.append({
                            "is_win": is_win,
                            "hour": hour,
                            "dow": dow,
                            "vol_ratio": vol_ratio,
                            "rsi": rsi_val,
                            "vwap_dist": vwap_dist
                        })
                        i = exit_idx
                    else:
                        i += 1
                    continue
        i += 1
        
    res_df = pd.DataFrame(trades)
    
    print("=== DEEP FILTER ANALYSIS (SOL 1M SCALPING) ===")
    print(f"Total Trades: {len(res_df)}")
    print(f"Overall Win Rate: {res_df['is_win'].mean()*100:.2f}%")
    
    print("\n--- Day of Week ---")
    print(res_df.groupby("dow")["is_win"].agg(['count', 'mean']).sort_values('mean', ascending=False))
    
    print("\n--- Time of Day (0-23 UTC) ---")
    res_df['session'] = pd.cut(res_df['hour'], bins=[-1, 6, 12, 18, 24], labels=['Asian(0-6)', 'London(6-12)', 'NY(12-18)', 'LateNY(18-24)'])
    print(res_df.groupby("session")["is_win"].agg(['count', 'mean']).sort_values('mean', ascending=False))
    
    print("\n--- RSI at Entry ---")
    res_df['rsi_bin'] = pd.qcut(res_df['rsi'], 3, duplicates='drop')
    print(res_df.groupby("rsi_bin")["is_win"].agg(['count', 'mean']))
    
    print("\n--- Volume Ratio (vs 20SMA) ---")
    res_df['vol_bin'] = pd.qcut(res_df['vol_ratio'], 3, duplicates='drop')
    print(res_df.groupby("vol_bin")["is_win"].agg(['count', 'mean']))
    
    print("\n--- Distance from VWAP (%) ---")
    res_df['vwap_bin'] = pd.qcut(res_df['vwap_dist'], 3, duplicates='drop')
    print(res_df.groupby("vwap_bin")["is_win"].agg(['count', 'mean']))

asyncio.run(run())
