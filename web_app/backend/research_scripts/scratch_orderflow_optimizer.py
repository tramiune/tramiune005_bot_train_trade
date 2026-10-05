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
    
    closes = df_15m['close'].values
    highs = df_15m['high'].values
    lows = df_15m['low'].values
    opens = df_15m['open'].values
    vols = df_15m['volume'].values
    vol_mas = df_15m['vol_ma'].values
    deltas = df_15m['delta'].values
    
    # Pre-calculate entry signals to make backtest hyper-fast
    signals = np.zeros(len(df_15m))
    for i in range(50, len(df_15m)-1):
        crange = highs[i] - lows[i]
        if crange == 0: continue
        close_pos = (closes[i] - lows[i]) / crange
        
        # COMBINED SHORT STRATEGY: Fade FOMO or Momentum Panic
        fade_fomo = vols[i] > 1.5 * vol_mas[i] and deltas[i] > 0.3 * vols[i] and close_pos > 0.7
        mom_panic = vols[i] > 1.5 * vol_mas[i] and deltas[i] < -0.3 * vols[i] and close_pos < 0.3
        
        if fade_fomo or mom_panic:
            signals[i] = -1 # Entry signal for next candle
            
    fee = 0.05 / 100
    results = []
    
    tps = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0]
    sls = [1.0, 1.5, 2.0, 3.0, 4.0, 5.0]
    
    print("Running optimization grid...")
    for sl_pct in sls:
        for tp_pct in tps:
            trades = []
            in_pos = False
            tp_price, sl_price = 0, 0
            for i in range(50, len(df_15m)-1):
                if not in_pos:
                    if signals[i] == -1:
                        in_pos = True
                        entry_p = opens[i+1]
                        tp_price = entry_p * (1 - tp_pct/100)
                        sl_price = entry_p * (1 + sl_pct/100)
                else:
                    if highs[i] >= sl_price:
                        trades.append(-sl_pct - fee*200)
                        in_pos = False
                    elif lows[i] <= tp_price:
                        trades.append(tp_pct - fee*200)
                        in_pos = False
                        
            if len(trades) > 0:
                tr = np.array(trades)
                wr = (tr > 0).mean() * 100
                pnl = tr.sum()
                results.append({'TP': tp_pct, 'SL': sl_pct, 'Trades': len(tr), 'WR': wr, 'PnL': pnl})
                
    res_df = pd.DataFrame(results).sort_values(by='PnL', ascending=False)
    print("\nTOP 10 BEST PARAMS (COMBINED SHORT STRATEGY):")
    print(res_df.head(10).to_string(index=False))

run()
