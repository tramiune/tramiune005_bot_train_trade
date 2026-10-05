import asyncio
import pandas as pd
import numpy as np
import sys, os
sys.path.insert(0, os.path.abspath(".agents/skills/honest-backtest/scripts"))
import bt_data

def run():
    print("Loading DOGE 1m data...")
    df = bt_data.load("DOGEUSDT", "1m")
    df.set_index(pd.to_datetime(df['time'], unit='s'), inplace=True)
    print("Resampling to 15m...")
    df_15m = df.resample('15min').agg({
        'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
    }).dropna()
    
    B = df_15m
    c, h, l, v = B["close"], B["high"], B["low"], B["volume"]
    
    # Calculate True Range
    h_c = h - c.shift()
    l_c = l - c.shift()
    tr = pd.concat([h - l, h_c.abs(), l_c.abs()], axis=1).max(axis=1)
    
    a = tr.rolling(20).mean()
    mid = c.rolling(20).mean()
    sd = c.rolling(20).std()
    
    # Squeeze ON
    on = (mid + 2 * sd < mid + 1.5 * a) & (mid - 2 * sd > mid - 1.5 * a)
    # Consecutive ON
    dur = on.groupby((~on).cumsum()).cumsum()
    
    # Fire event
    fire = (~on) & on.shift(1, fill_value=False) & (dur.shift(1) >= 5) & (v > 1.5 * v.rolling(20).mean())
    bull = c > mid
    
    # We test both Follow (Trend) and Contra (Fade)
    sig_follow = np.where(fire, np.where(bull, 1, -1), 0)
    sig_contra = np.where(fire, np.where(bull, -1, 1), 0)
    
    opens = B["open"].values
    highs = B["high"].values
    lows = B["low"].values
    
    tps = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0]
    sls = [1.0, 1.5, 2.0, 3.0, 4.0, 5.0]
    fee = 0.05 / 100
    
    def backtest(signals, name):
        results = []
        for tp_pct in tps:
            for sl_pct in sls:
                trades = []
                in_pos = False
                tp_price = 0; sl_price = 0; side = 0
                for i in range(20, len(B)-1):
                    if not in_pos:
                        if signals[i] != 0:
                            in_pos = True
                            side = signals[i]
                            entry_p = opens[i+1]
                            if side == 1:
                                tp_price = entry_p * (1 + tp_pct/100)
                                sl_price = entry_p * (1 - sl_pct/100)
                            else:
                                tp_price = entry_p * (1 - tp_pct/100)
                                sl_price = entry_p * (1 + sl_pct/100)
                    else:
                        if side == 1:
                            if lows[i] <= sl_price:
                                trades.append(-sl_pct - fee*200)
                                in_pos = False
                            elif highs[i] >= tp_price:
                                trades.append(tp_pct - fee*200)
                                in_pos = False
                        else:
                            if highs[i] >= sl_price:
                                trades.append(-sl_pct - fee*200)
                                in_pos = False
                            elif lows[i] <= tp_price:
                                trades.append(tp_pct - fee*200)
                                in_pos = False
                
                tr = np.array(trades)
                if len(tr) > 0:
                    wr = (tr > 0).mean() * 100
                    results.append({'Mode': name, 'TP': tp_pct, 'SL': sl_pct, 'Trades': len(tr), 'WR': wr, 'PnL': tr.sum()})
        return results

    print("Optimizing Squeeze Follow...")
    res_f = backtest(sig_follow, 'FOLLOW')
    print("Optimizing Squeeze Contra...")
    res_c = backtest(sig_contra, 'CONTRA')
    
    res_df = pd.DataFrame(res_f + res_c).sort_values(by='PnL', ascending=False)
    print("\n=== TOP 15 MỐC TP/SL (DOGE 15M SQUEEZE) - 4 NĂM ===")
    print("One Shot, One Kill (Không nhồi lệnh)")
    print(res_df.head(15).to_string(index=False))

run()
