import asyncio
import pandas as pd
import numpy as np
import sys, os
sys.path.insert(0, os.path.abspath(".agents/skills/honest-backtest/scripts"))
import bt_data

def run():
    df = bt_data.load("DOGEUSDT", "1m")
    df.set_index(pd.to_datetime(df['time'], unit='s'), inplace=True)
    df_15m = df.resample('15min').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum', 'taker_buy_volume': 'sum'}).dropna()
    df_15m['delta'] = 2 * df_15m['taker_buy_volume'] - df_15m['volume']
    df_15m['vol_ma'] = df_15m['volume'].rolling(50).mean()
    
    trades = []
    in_position = False
    current_side = 0
    entry_price, tp_price, sl_price = 0, 0, 0
    entry_time = None
    fee = 0.05 / 100
    
    closes, highs, lows, opens, vols, vol_mas, deltas = df_15m['close'].values, df_15m['high'].values, df_15m['low'].values, df_15m['open'].values, df_15m['volume'].values, df_15m['vol_ma'].values, df_15m['delta'].values
    dts = df_15m.index
    
    for i in range(50, len(df_15m)-1):
        if not in_position:
            crange = highs[i] - lows[i]
            if crange == 0: continue
            close_pos = (closes[i] - lows[i]) / crange
            
            # SHORT CONDITION (Fade FOMO)
            if vols[i] > 1.5 * vol_mas[i] and deltas[i] > 0.3 * vols[i] and close_pos > 0.7:
                in_position = True; current_side = -1
                entry_price = opens[i+1]; entry_time = dts[i+1]
                tp_price = entry_price * 0.97
                sl_price = entry_price * 1.015
                
            # LONG CONDITION (Fade Panic)
            elif vols[i] > 1.5 * vol_mas[i] and deltas[i] < -0.3 * vols[i] and close_pos < 0.3:
                in_position = True; current_side = 1
                entry_price = opens[i+1]; entry_time = dts[i+1]
                tp_price = entry_price * 1.03
                sl_price = entry_price * 0.985
                
        else:
            if current_side == -1: # SHORT
                if highs[i] >= sl_price:
                    trades.append({'time': dts[i], 'pnl': -1.5 - fee*200, 'side': 'SHORT'})
                    in_position = False
                elif lows[i] <= tp_price:
                    trades.append({'time': dts[i], 'pnl': 3.0 - fee*200, 'side': 'SHORT'})
                    in_position = False
            elif current_side == 1: # LONG
                if lows[i] <= sl_price:
                    trades.append({'time': dts[i], 'pnl': -1.5 - fee*200, 'side': 'LONG'})
                    in_position = False
                elif highs[i] >= tp_price:
                    trades.append({'time': dts[i], 'pnl': 3.0 - fee*200, 'side': 'LONG'})
                    in_position = False
                
    res_df = pd.DataFrame(trades)
    
    # Analyze results
    print("=== ORDER FLOW FADE (LONG & SHORT) ===")
    
    total_trades = len(res_df)
    total_longs = len(res_df[res_df['side'] == 'LONG'])
    total_shorts = len(res_df[res_df['side'] == 'SHORT'])
    win_longs = len(res_df[(res_df['side'] == 'LONG') & (res_df['pnl'] > 0)])
    win_shorts = len(res_df[(res_df['side'] == 'SHORT') & (res_df['pnl'] > 0)])
    
    print(f"Tổng lệnh: {total_trades} (Long: {total_longs}, Short: {total_shorts})")
    if total_longs > 0: print(f"Win Rate LONG: {win_longs/total_longs*100:.2f}%")
    if total_shorts > 0: print(f"Win Rate SHORT: {win_shorts/total_shorts*100:.2f}%")
    print(f"Tổng PnL: {res_df['pnl'].sum():.2f}%\n")
    
    res_df['year'] = res_df['time'].dt.year
    res_df['month'] = res_df['time'].dt.month
    
    yearly = res_df.groupby('year').agg(
        trades=('pnl', 'count'),
        wins=('pnl', lambda x: (x > 0).sum()),
        pnl=('pnl', 'sum')
    ).reset_index()
    
    print("Year | Trades | Wins | Win Rate | PnL")
    print("-" * 45)
    for _, row in yearly.iterrows():
        wr = (row['wins'] / row['trades']) * 100 if row['trades'] > 0 else 0
        print(f"{int(row['year'])} | {int(row['trades']):6d} | {int(row['wins']):4d} |   {wr:5.1f}% | {row['pnl']:6.2f}%")
        
run()
