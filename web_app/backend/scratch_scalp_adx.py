import asyncio
import pandas as pd
import numpy as np
from engine.exchange import BinanceFutures

# Technical Indicators
def calculate_vwap(df):
    q = df['volume'] * ((df['high'] + df['low'] + df['close']) / 3)
    return q.rolling(window=1440).sum() / df['volume'].rolling(window=1440).sum()

def calculate_adx(df, period=14):
    plus_dm = df['high'].diff()
    minus_dm = df['low'].diff(-1).abs() # Rough approximation for speed
    
    # Accurate TR
    tr1 = df['high'] - df['low']
    tr2 = (df['high'] - df['close'].shift()).abs()
    tr3 = (df['low'] - df['close'].shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()
    
    plus_di = 100 * (plus_dm.ewm(alpha=1/period, adjust=False).mean() / atr)
    minus_di = 100 * (minus_dm.ewm(alpha=1/period, adjust=False).mean() / atr)
    
    dx = (abs(plus_di - minus_di) / (plus_di + minus_di)) * 100
    adx = dx.ewm(alpha=1/period, adjust=False).mean()
    return adx, atr

async def run():
    ex = BinanceFutures()
    from fetch_more import fetch_lots_of_klines
    print("Fetching data...")
    data = await fetch_lots_of_klines(ex.exchange, "SOL/USDT", "1m", 20000)
    df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    
    print("Calculating indicators...")
    df['ema9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['vwap'] = calculate_vwap(df)
    
    # Add ADX & ATR
    adx, atr = calculate_adx(df, 14)
    df['adx'] = adx
    df['atr_pct'] = (atr / df['close']) * 100
    
    tp_pct = 1.5
    sl_pct = 0.7
    trades = []
    
    print("Backtesting...")
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
                        trades.append({
                            "is_win": is_win,
                            "adx": df['adx'].iloc[i],
                            "atr_pct": df['atr_pct'].iloc[i],
                        })
                        i = exit_idx
                    else:
                        i += 1
                    continue
        i += 1
        
    res_df = pd.DataFrame(trades)
    print(f"Original Trades: {len(res_df)} (Wins: {res_df['is_win'].sum()}, Losses: {len(res_df)-res_df['is_win'].sum()})")
    
    # Try filtering with ADX
    for adx_thresh in [15, 20, 25, 30]:
        f = res_df[res_df['adx'] > adx_thresh]
        if len(f) > 0:
            w = f['is_win'].sum()
            print(f"ADX > {adx_thresh}: Trades: {len(f)}, Wins: {w}, Losses: {len(f)-w}, WinRate: {w/len(f)*100:.1f}%")
            
    # Try filtering with ATR
    for atr_thresh in [0.05, 0.08, 0.1, 0.15]:
        f = res_df[res_df['atr_pct'] > atr_thresh]
        if len(f) > 0:
            w = f['is_win'].sum()
            print(f"ATR > {atr_thresh}%: Trades: {len(f)}, Wins: {w}, Losses: {len(f)-w}, WinRate: {w/len(f)*100:.1f}%")

asyncio.run(run())
