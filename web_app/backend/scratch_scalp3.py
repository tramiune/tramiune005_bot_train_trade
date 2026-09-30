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
    
    results = []
    
    # We will test Market (Taker 0.04% + 0.05% slippage) vs Limit (Maker 0.02% + 0% slippage)
    taker_fee_total = 0.04/100 + 0.05/100 # Fee + Assumed Slippage
    maker_fee_total = 0.02/100 # Just maker fee
    
    for tp_pct in [1.5, 2.0, 3.0]:
        for sl_pct in [0.7, 1.0]:
            trades = []
            gross_profit_pct = 0
            
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
                                if is_win:
                                    trades.append(1)
                                else:
                                    trades.append(0)
                                i = exit_idx
                            else:
                                i += 1
                            continue
                i += 1
                
            if len(trades) > 0:
                wins = sum(trades)
                wr = wins / len(trades) * 100
                
                # Calculate PnL for Market (Taker + Slippage)
                market_pnl = (wins * (tp_pct - (taker_fee_total * 2 * 100))) - ((len(trades)-wins) * (sl_pct + (taker_fee_total * 2 * 100)))
                
                # Calculate PnL for Limit (Maker + No Slippage)
                limit_pnl = (wins * (tp_pct - (maker_fee_total * 2 * 100))) - ((len(trades)-wins) * (sl_pct + (maker_fee_total * 2 * 100)))
                
                results.append({
                    "TP_%": tp_pct,
                    "SL_%": sl_pct,
                    "Trades": len(trades),
                    "WinRate": wr,
                    "Market_PnL_%": market_pnl,
                    "Limit_PnL_%": limit_pnl,
                    "Extra_Profit_%": limit_pnl - market_pnl
                })
                
    res_df = pd.DataFrame(results)
    res_df = res_df.sort_values(by="Limit_PnL_%", ascending=False)
    print("\n=== MARKET vs LIMIT SCALPING RESULTS (SOL/USDT 1m) ===")
    print(res_df.to_string(index=False))

asyncio.run(run())
