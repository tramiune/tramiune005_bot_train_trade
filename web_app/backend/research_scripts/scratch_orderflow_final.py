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
    in_pos = False
    entry_price, tp_price, sl_price = 0, 0, 0
    entry_time = None
    fee = 0.05 / 100
    
    tp_pct = 6.0
    sl_pct = 5.0
    
    closes, highs, lows, opens, vols, vol_mas, deltas = df_15m['close'].values, df_15m['high'].values, df_15m['low'].values, df_15m['open'].values, df_15m['volume'].values, df_15m['vol_ma'].values, df_15m['delta'].values
    dts = df_15m.index
    
    for i in range(50, len(df_15m)-1):
        if not in_pos:
            crange = highs[i] - lows[i]
            if crange == 0: continue
            close_pos = (closes[i] - lows[i]) / crange
            
            fade_fomo = vols[i] > 1.5 * vol_mas[i] and deltas[i] > 0.3 * vols[i] and close_pos > 0.7
            mom_panic = vols[i] > 1.5 * vol_mas[i] and deltas[i] < -0.3 * vols[i] and close_pos < 0.3
            
            if fade_fomo or mom_panic:
                in_pos = True
                entry_price = opens[i+1]; entry_time = dts[i+1]
                tp_price = entry_price * (1 - tp_pct/100.0) # SHORT
                sl_price = entry_price * (1 + sl_pct/100.0) # SHORT
                
        else:
            if highs[i] >= sl_price:
                trades.append({'time': entry_time, 'exit': dts[i], 'pnl': -sl_pct - fee*200})
                in_pos = False
            elif lows[i] <= tp_price:
                trades.append({'time': entry_time, 'exit': dts[i], 'pnl': tp_pct - fee*200})
                in_pos = False
                
    res_df = pd.DataFrame(trades)
    res_df['year'] = res_df['exit'].dt.year
    res_df['month'] = res_df['exit'].dt.month
    
    print("=== ORDER FLOW SHORT (TP 6.0%, SL 5.0%) - 1 LỆNH DUY NHẤT/THỜI ĐIỂM ===")
    
    monthly = res_df.groupby(['year', 'month']).agg(
        trades=('pnl', 'count'),
        wins=('pnl', lambda x: (x > 0).sum()),
        pnl=('pnl', 'sum')
    ).reset_index()
    
    print("Năm-Tháng | Lệnh | Thắng | Win Rate | PnL ròng (1x)")
    print("-" * 55)
    for _, row in monthly.iterrows():
        wr = (row['wins'] / row['trades']) * 100 if row['trades'] > 0 else 0
        print(f"{int(row['year'])}-{int(row['month']):02d}    | {int(row['trades']):4d} | {int(row['wins']):4d}  |   {wr:5.1f}% | {row['pnl']:6.2f}%")
        
    yearly = res_df.groupby('year').agg(
        trades=('pnl', 'count'),
        wins=('pnl', lambda x: (x > 0).sum()),
        pnl=('pnl', 'sum')
    ).reset_index()
    
    print("\n--- TỔNG KẾT THEO NĂM ---")
    print("Năm  | Lệnh | Thắng | Win Rate | PnL ròng")
    for _, row in yearly.iterrows():
        wr = (row['wins'] / row['trades']) * 100 if row['trades'] > 0 else 0
        print(f"{int(row['year'])} | {int(row['trades']):4d} | {int(row['wins']):4d}  |   {wr:5.1f}% | {row['pnl']:6.2f}%")
        
    print(f"\nTỔNG KẾT 4 NĂM: {len(res_df)} Lệnh | Win Rate {(res_df['pnl']>0).mean()*100:.2f}% | PnL: +{res_df['pnl'].sum():.2f}%")

run()
