import asyncio
import pandas as pd
import numpy as np
import time
import ccxt.async_support as ccxt

async def fetch_data(exchange, symbol, tf='1h', days=180):
    now = int(time.time() * 1000)
    ms = days * 24 * 60 * 60 * 1000
    since = now - ms
    all_klines = []
    while since < now:
        try:
            klines = await exchange.fetch_ohlcv(symbol, tf, since=since, limit=1500)
            if not klines: break
            all_klines.extend(klines)
            since = klines[-1][0] + (60 * 60 * 1000)
        except Exception:
            await asyncio.sleep(0.5)
    
    df = pd.DataFrame(all_klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df = df.drop_duplicates(subset=['timestamp']).set_index('timestamp')
    return df

async def main():
    exchange = ccxt.binanceusdm({'enableRateLimit': True})
    
    print("Fetching 180 days 1h data for DOGE and OP...")
    doge_df = await fetch_data(exchange, 'DOGE/USDT', '1h', 180)
    op_df = await fetch_data(exchange, 'OP/USDT', '1h', 180)
    await exchange.close()
    
    df = doge_df[['close']].join(op_df[['close']], lsuffix='_doge', rsuffix='_op').dropna()
    df.reset_index(inplace=True)
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
    
    # Calculate Ratio DOGE / OP
    df['ratio'] = df['close_doge'] / df['close_op']
    
    window = 100 # 100 hours rolling mean
    df['ratio_mean'] = df['ratio'].rolling(window=window).mean()
    df['ratio_std'] = df['ratio'].rolling(window=window).std()
    df['z_score'] = (df['ratio'] - df['ratio_mean']) / df['ratio_std']
    
    trades = []
    in_position = False
    current_side = 0 # 1: LONG DOGE/SHORT OP, -1: SHORT DOGE/LONG OP
    entry_doge = 0.0
    entry_op = 0.0
    entry_time = None
    
    fee_rate = 0.05 / 100 # Taker fee
    
    for i in range(window, len(df)):
        z = df['z_score'].iloc[i]
        c_doge = df['close_doge'].iloc[i]
        c_op = df['close_op'].iloc[i]
        
        if not in_position:
            if z < -2.0:
                # DOGE is cheap, OP is expensive
                in_position = True
                current_side = 1
                entry_doge = c_doge
                entry_op = c_op
                entry_time = df['datetime'].iloc[i]
            elif z > 2.0:
                # DOGE is expensive, OP is cheap
                in_position = True
                current_side = -1
                entry_doge = c_doge
                entry_op = c_op
                entry_time = df['datetime'].iloc[i]
        else:
            is_exit = False
            
            # Exit on mean reversion (Z crosses 0) or Stop Loss (Z > 4)
            if current_side == 1 and (z >= 0 or z < -4.0):
                is_exit = True
            elif current_side == -1 and (z <= 0 or z > 4.0):
                is_exit = True
                
            if is_exit:
                if current_side == 1:
                    doge_pnl = (c_doge - entry_doge) / entry_doge
                    op_pnl = (entry_op - c_op) / entry_op
                else:
                    doge_pnl = (entry_doge - c_doge) / entry_doge
                    op_pnl = (c_op - entry_op) / entry_op
                    
                net_pnl = (doge_pnl + op_pnl)/2.0 - (fee_rate * 2) # Div by 2 because capital is split 50/50
                
                trades.append({
                    "entry_time": entry_time,
                    "exit_time": df['datetime'].iloc[i],
                    "side": "LONG DOGE/SHORT OP" if current_side == 1 else "SHORT DOGE/LONG OP",
                    "pnl_pct": net_pnl * 100
                })
                
                in_position = False
                current_side = 0

    res_df = pd.DataFrame(trades)
    
    if len(res_df) == 0:
        print("No trades")
        return
        
    wins = res_df[res_df['pnl_pct'] > 0]
    wr = len(wins) / len(res_df) * 100
    total_pnl = res_df['pnl_pct'].sum()
    
    print("\n=== DOGE vs OP PAIRS TRADING (6 MONTHS) ===")
    print(f"Trades: {len(res_df)}")
    print(f"Win Rate: {wr:.2f}%")
    print(f"Total PnL (1x Leverage): +{total_pnl:.2f}%")
    print(f"Average PnL per trade: {res_df['pnl_pct'].mean():.2f}%")
    
asyncio.run(main())
