import pandas as pd
import numpy as np
import sys, os
sys.path.insert(0, os.path.abspath(".agents/skills/honest-backtest/scripts"))
import bt_data

def run():
    df = bt_data.load("DOGEUSDT", "1m")
    df.set_index(pd.to_datetime(df['time'], unit='s'), inplace=True)
    B = df.resample('4h').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'}).dropna()
    c, h, l = B["close"].values, B["high"].values, B["low"].values
    opens, dts = B["open"].values, B.index
    
    lengths = [10, 14, 20, 30]
    mults = [2.0, 3.0, 4.0, 5.0]
    
    results = []
    
    for length in lengths:
        for multiplier in mults:
            tr1 = h - l
            tr2 = np.abs(h - np.roll(c, 1))
            tr3 = np.abs(l - np.roll(c, 1))
            tr = np.maximum(tr1, np.maximum(tr2, tr3))
            tr[0] = 0
            
            atr = pd.Series(tr).rolling(length).mean().values
            hl2 = (h + l) / 2
            
            upper_band = hl2 + (multiplier * atr)
            lower_band = hl2 - (multiplier * atr)
            
            in_uptrend = np.ones(len(B), dtype=bool)
            
            for i in range(1, len(B)):
                if c[i] > upper_band[i-1]:
                    in_uptrend[i] = True
                elif c[i] < lower_band[i-1]:
                    in_uptrend[i] = False
                else:
                    in_uptrend[i] = in_uptrend[i-1]
                    if in_uptrend[i] and lower_band[i] < lower_band[i-1]:
                        lower_band[i] = lower_band[i-1]
                    if not in_uptrend[i] and upper_band[i] > upper_band[i-1]:
                        upper_band[i] = upper_band[i-1]
                        
            trades = []
            in_pos = False; entry_p = 0
            
            for i in range(length, len(B)-1):
                if not in_pos:
                    if not in_uptrend[i-1] and in_uptrend[i]:
                        in_pos = True
                        entry_p = opens[i+1]
                else:
                    if in_uptrend[i-1] and not in_uptrend[i]:
                        exit_p = opens[i+1]
                        trades.append(((exit_p - entry_p) / entry_p) * 100 - 0.1)
                        in_pos = False
                        
            if len(trades) > 0:
                tr_arr = np.array(trades)
                results.append({
                    'Length': length,
                    'Mult': multiplier,
                    'Trades': len(tr_arr),
                    'Win Rate': f"{(tr_arr > 0).mean()*100:.1f}%",
                    'PnL': round(tr_arr.sum(), 2)
                })
                
    df_res = pd.DataFrame(results).sort_values(by='PnL', ascending=False)
    print("=== TỐI ƯU HÓA SUPERTREND 4H ===")
    print(df_res.head(10).to_string(index=False))

run()
