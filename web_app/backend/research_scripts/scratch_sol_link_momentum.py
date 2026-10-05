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
    print("Fetching 4 years for SOL and LINK...")
    sol_df = await fetch_data(exchange, 'SOL/USDT', '1h', 4)
    link_df = await fetch_data(exchange, 'LINK/USDT', '1h', 4)
    await exchange.close()
    
    df = sol_df[['close']].join(link_df[['close']], lsuffix='_sol', rsuffix='_link').dropna()
    df.reset_index(inplace=True)
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
    
    df['ratio'] = df['close_sol'] / df['close_link']
    window = 100
    df['ratio_mean'] = df['ratio'].rolling(window=window).mean()
    df['ratio_std'] = df['ratio'].rolling(window=window).std()
    df['z_score'] = (df['ratio'] - df['ratio_mean']) / df['ratio_std']
    
    # PARAMETERS FOR MOMENTUM / TREND FOLLOWING THE SPREAD
    ENTRY_Z = 2.0
    TP_Z = 5.0 # Trend continues!
    
    trades = []
    in_position = False
    current_side = 0
    entry_sol = 0.0
    entry_link = 0.0
    entry_time = None
    fee_rate = 0.05 / 100
    
    for i in range(window, len(df)):
        z = df['z_score'].iloc[i]
        c_sol = df['close_sol'].iloc[i]
        c_link = df['close_link'].iloc[i]
        
        if not in_position:
            # MOMENTUM ENTRY (ĐÁNH NGƯỢC)
            if z > ENTRY_Z:
                # SOL đang phá đỉnh so với LINK -> LONG SOL, SHORT LINK (Đu theo trend)
                in_position = True; current_side = 1
                entry_sol = c_sol; entry_link = c_link
                entry_time = df['datetime'].iloc[i]
            elif z < -ENTRY_Z:
                # SOL đang phá đáy so với LINK -> SHORT SOL, LONG LINK
                in_position = True; current_side = -1
                entry_sol = c_sol; entry_link = c_link
                entry_time = df['datetime'].iloc[i]
        else:
            is_exit = False
            
            # EXIT LOGIC
            if current_side == 1:
                # LONG SOL, SHORT LINK. 
                # Chốt lời nếu Z tiếp tục bay lên 5.0
                # Cắt lỗ nếu Z quay đầu về 0 (Mean Reversion - Phá đỉnh giả)
                if z >= TP_Z or z <= 0:
                    is_exit = True
            elif current_side == -1:
                if z <= -TP_Z or z >= 0:
                    is_exit = True
                
            if is_exit:
                if current_side == 1:
                    sol_pnl = (c_sol - entry_sol) / entry_sol
                    link_pnl = (entry_link - c_link) / entry_link
                else:
                    sol_pnl = (entry_sol - c_sol) / entry_sol
                    link_pnl = (c_link - entry_link) / entry_link
                    
                net_pnl = (sol_pnl + link_pnl)/2.0 - (fee_rate * 2)
                
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
    
    print("\n=== SPREAD MOMENTUM TRADING (SOL vs LINK) ===")
    print(f"Logic: Vào khi Z>{ENTRY_Z} (Đu trend). Chốt lời Z={TP_Z}. Cắt lỗ Z=0")
    print("Year | Trades | Wins | Win Rate | Net PnL (1x)")
    print("-" * 55)
    for _, row in yearly_stats.iterrows():
        wr = (row['wins'] / row['trades']) * 100 if row['trades'] > 0 else 0
        print(f"{int(row['year'])} | {int(row['trades']):6d} | {int(row['wins']):4d} |   {wr:5.1f}% | {row['pnl']:10.2f}%")
        
    print("-" * 55)
    total_trades = len(res_df)
    total_wins = len(res_df[res_df['pnl_pct'] > 0])
    total_pnl = res_df['pnl_pct'].sum()
    print(f"Total Trades: {total_trades}")
    print(f"Win Rate: {(total_wins/total_trades)*100:.2f}%")
    print(f"Total Net PnL (1x): {total_pnl:.2f}%")
    
asyncio.run(main())
