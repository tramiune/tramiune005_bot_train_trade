import asyncio
import pandas as pd
import numpy as np
from engine.exchange import BinanceFutures

# Calculate VWAP
def calculate_vwap(df):
    q = df['volume'] * ((df['high'] + df['low'] + df['close']) / 3)
    # We approximate VWAP by a rolling window instead of anchored for simplicity in 1m
    # Let's use a 1-day rolling window for 1m (1440 minutes)
    return q.rolling(window=1440).sum() / df['volume'].rolling(window=1440).sum()

async def run():
    ex = BinanceFutures()
    from fetch_more import fetch_lots_of_klines
    print("Fetching SOL 1m data... (20,000 candles = ~14 days)")
    data = await fetch_lots_of_klines(ex.exchange, "SOL/USDT", "1m", 20000)
    df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    
    print("Calculating indicators...")
    df['ema9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['vwap'] = calculate_vwap(df)
    
    results = []
    
    fee_rate = 0.0004 # 0.04% taker fee
    
    # Grid search parameters
    for tp_pct in [0.3, 0.5, 0.8]:
        for sl_pct in [0.2, 0.3, 0.4]:
            trades = []
            gross_profit_pct = 0
            
            i = 1500
            while i < len(df) - 1:
                # LONG Setup:
                # 1. Price above daily VWAP
                # 2. EMA9 > EMA21
                # 3. Price pulled back to touch EMA21
                
                if df['close'].iloc[i] > df['vwap'].iloc[i]:
                    if df['ema9'].iloc[i] > df['ema21'].iloc[i]:
                        if df['low'].iloc[i] <= df['ema21'].iloc[i] and df['close'].iloc[i] > df['ema21'].iloc[i]:
                            
                            entry_price = df['close'].iloc[i]
                            sl = entry_price * (1 - sl_pct/100)
                            tp = entry_price * (1 + tp_pct/100)
                            
                            is_win = False
                            exit_idx = i
                            for j in range(i+1, min(i+120, len(df))): # Max holding 120 mins
                                if df['low'].iloc[j] <= sl:
                                    is_win = False
                                    exit_idx = j
                                    break
                                elif df['high'].iloc[j] >= tp:
                                    is_win = True
                                    exit_idx = j
                                    break
                                    
                            if exit_idx > i:
                                if is_win:
                                    # PnL = TP% - (Entry Fee + Exit Fee)
                                    gross_profit_pct += (tp_pct - (fee_rate * 2 * 100))
                                    trades.append(1)
                                else:
                                    gross_profit_pct -= (sl_pct + (fee_rate * 2 * 100))
                                    trades.append(0)
                                i = exit_idx
                            else:
                                i += 1
                            continue
                i += 1
                
            if len(trades) > 0:
                wins = sum(trades)
                wr = wins / len(trades) * 100
                results.append({
                    "TP_%": tp_pct,
                    "SL_%": sl_pct,
                    "Trades": len(trades),
                    "WinRate": wr,
                    "NetPnL_%": gross_profit_pct
                })
                
    res_df = pd.DataFrame(results)
    res_df = res_df.sort_values(by="NetPnL_%", ascending=False)
    print("\n=== SCALPING 1M RESULTS (SOL/USDT, VWAP + EMA Pullback) ===")
    print(res_df.to_string(index=False))

asyncio.run(run())
