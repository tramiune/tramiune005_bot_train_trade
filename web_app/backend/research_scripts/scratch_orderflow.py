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
    entry_price, tp_price, sl_price = 0, 0, 0
    fee = 0.05 / 100
    
    closes, highs, lows, opens, vols, vol_mas, deltas = df_15m['close'].values, df_15m['high'].values, df_15m['low'].values, df_15m['open'].values, df_15m['volume'].values, df_15m['vol_ma'].values, df_15m['delta'].values
    
    for i in range(50, len(df_15m)-1):
        if not in_position:
            # FADE RETAIL FOMO (ĐÁNH NGƯỢC CÁ MẬP / RETAIL)
            # Huge green candle, massive buy delta
            if vols[i] > 1.5 * vol_mas[i] and deltas[i] > 0.3 * vols[i]:
                crange = highs[i] - lows[i]
                if crange > 0 and (closes[i] - lows[i])/crange > 0.7:
                    in_position = True
                    entry_price = opens[i+1]
                    tp_price = entry_price * 0.97 # TP 3% down
                    sl_price = entry_price * 1.015 # SL 1.5% up
        else:
            if highs[i] >= sl_price:
                trades.append(-1.5 - fee*200)
                in_position = False
            elif lows[i] <= tp_price:
                trades.append(3.0 - fee*200)
                in_position = False
                
    res = pd.Series(trades)
    print(f"Tổng Lệnh: {len(res)} | Win Rate: {(res>0).mean()*100:.2f}% | PnL: {res.sum():.2f}%")
run()
