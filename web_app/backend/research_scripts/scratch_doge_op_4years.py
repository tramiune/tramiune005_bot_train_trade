import asyncio
import pandas as pd
import numpy as np
import time
import ccxt.async_support as ccxt

async def fetch_data(exchange, symbol, tf='1h', years=4):
    now = int(time.time() * 1000)
    ms = years * 365 * 24 * 60 * 60 * 1000
    since = now - ms
    all_klines = []
    print(f"Fetching {years} years for {symbol}...")
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
    doge_df = await fetch_data(exchange, 'DOGE/USDT', '1h', 4)
    op_df = await fetch_data(exchange, 'OP/USDT', '1h', 4)
    await exchange.close()
    
    df = doge_df[['close']].join(op_df[['close']], lsuffix='_doge', rsuffix='_op').dropna()
    df.reset_index(inplace=True)
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
    
    print(f"Data aligned. Total hours: {len(df)}")
    
    df['ratio'] = df['close_doge'] / df['close_op']
    window = 100
    df['ratio_mean'] = df['ratio'].rolling(window=window).mean()
    df['ratio_std'] = df['ratio'].rolling(window=window).std()
    df['z_score'] = (df['ratio'] - df['ratio_mean']) / df['ratio_std']
    
    trades = []
    in_position = False
    current_side = 0
    entry_doge = 0.0
    entry_op = 0.0
    entry_time = None
    fee_rate = 0.05 / 100
    
    for i in range(window, len(df)):
        z = df['z_score'].iloc[i]
        c_doge = df['close_doge'].iloc[i]
        c_op = df['close_op'].iloc[i]
        
        if not in_position:
            if z < -2.0:
                in_position = True; current_side = 1
                entry_doge = c_doge; entry_op = c_op
                entry_time = df['datetime'].iloc[i]
            elif z > 2.0:
                in_position = True; current_side = -1
                entry_doge = c_doge; entry_op = c_op
                entry_time = df['datetime'].iloc[i]
        else:
            is_exit = False
            if current_side == 1 and (z >= 0 or z < -4.0): is_exit = True
            elif current_side == -1 and (z <= 0 or z > 4.0): is_exit = True
                
            if is_exit:
                if current_side == 1:
                    doge_pnl = (c_doge - entry_doge) / entry_doge
                    op_pnl = (entry_op - c_op) / entry_op
                else:
                    doge_pnl = (entry_doge - c_doge) / entry_doge
                    op_pnl = (c_op - entry_op) / entry_op
                    
                net_pnl = (doge_pnl + op_pnl)/2.0 - (fee_rate * 2)
                
                trades.append({
                    "exit_time": df['datetime'].iloc[i],
                    "pnl_pct": net_pnl * 100
                })
                in_position = False; current_side = 0

    res_df = pd.DataFrame(trades)
    if len(res_df) == 0:
        print("No trades")
        return
        
    res_df['year'] = res_df['exit_time'].dt.year
    
    yearly_stats = res_df.groupby('year').agg(
        trades=('pnl_pct', 'count'),
        wins=('pnl_pct', lambda x: (x > 0).sum()),
        pnl=('pnl_pct', 'sum')
    ).reset_index()
    
    print("\nYear | Trades | Wins | Win Rate | Net PnL (1x)")
    print("-" * 55)
    for _, row in yearly_stats.iterrows():
        wr = (row['wins'] / row['trades']) * 100 if row['trades'] > 0 else 0
        print(f"{int(row['year'])} | {int(row['trades']):6d} | {int(row['wins']):4d} |   {wr:5.1f}% | {row['pnl']:10.2f}%")
        
    print("-" * 55)
    total_trades = len(res_df)
    total_wins = len(res_df[res_df['pnl_pct'] > 0])
    total_pnl = res_df['pnl_pct'].sum()
    print(f"OVERALL 4 YEARS:")
    print(f"Total Trades: {total_trades}")
    print(f"Win Rate: {(total_wins/total_trades)*100:.2f}%")
    print(f"Total Net PnL (1x): {total_pnl:.2f}%")
    
asyncio.run(main())
