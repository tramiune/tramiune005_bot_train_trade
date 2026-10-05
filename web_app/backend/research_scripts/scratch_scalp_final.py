import asyncio
import pandas as pd
import numpy as np
from engine.exchange import BinanceFutures

def calculate_vwap(df):
    q = df['volume'] * ((df['high'] + df['low'] + df['close']) / 3)
    return q.rolling(window=1440).sum() / df['volume'].rolling(window=1440).sum()

async def run():
    ex = BinanceFutures()
    from fetch_more import fetch_lots_of_klines
    data = await fetch_lots_of_klines(ex.exchange, "SOL/USDT", "1m", 20000)
    df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    
    df['ema9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['vwap'] = calculate_vwap(df)
    
    tp_pct = 1.5
    sl_pct = 0.7
    maker_fee_total = 0.02 / 100
    
    wins = 0
    losses = 0
    
    i = 1500
    while i < len(df) - 1:
        if df['close'].iloc[i] > df['vwap'].iloc[i]:
            if df['ema9'].iloc[i] > df['ema21'].iloc[i]:
                if df['low'].iloc[i] <= df['ema21'].iloc[i] and df['close'].iloc[i] > df['ema21'].iloc[i]:
                    
                    entry_price = df['close'].iloc[i]
                    vwap_dist = ((entry_price - df["vwap"].iloc[i]) / df["vwap"].iloc[i]) * 100
                    hour = pd.to_datetime(df["timestamp"].iloc[i], unit='ms').hour
                    
                    # APPLY FILTERS
                    if vwap_dist > 0.8 and (12 <= hour <= 18):
                        
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
                            if is_win:
                                wins += 1
                            else:
                                losses += 1
                            i = exit_idx
                        else:
                            i += 1
                        continue
        i += 1
        
    total_trades = wins + losses
    wr = (wins / total_trades * 100) if total_trades > 0 else 0
    
    limit_pnl = (wins * (tp_pct - (maker_fee_total * 2 * 100))) - (losses * (sl_pct + (maker_fee_total * 2 * 100)))
    
    print("\n=== FINAL GOLDEN SCALPING STRATEGY (SOL 1M) ===")
    print(f"Total Trades: {total_trades}")
    print(f"Wins: {wins}")
    print(f"Losses: {losses}")
    print(f"Win Rate: {wr:.2f}%")
    print(f"Net Profit (Limit Order): +{limit_pnl:.2f}%")

asyncio.run(run())
