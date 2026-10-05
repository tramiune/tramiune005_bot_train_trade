import asyncio
import pandas as pd
import numpy as np
import sys, os
sys.path.insert(0, os.path.abspath(".agents/skills/honest-backtest/scripts"))
import bt_data

def run():
    df = bt_data.load("DOGEUSDT", "1m")
    df.set_index(pd.to_datetime(df['time'], unit='s'), inplace=True)
    B = df.resample('15min').agg({
        'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
    }).dropna()
    
    c, h, l, o = B["close"], B["high"], B["low"], B["open"]
    support = l.shift(5).rolling(100).min()
    pierce = (l < support) & (l >= support * 0.98) & (c > support)
    candle_range = h - l
    close_pos = (c - l) / candle_range.replace(0, np.nan)
    fire_long = pierce & (close_pos > 0.5)
    sig = np.where(fire_long, 1, 0)
    
    opens = B["open"].values
    highs = B["high"].values
    lows = B["low"].values
    dts = B.index
    
    # Original: LONG, SL tight, TP 5x
    # Inverse: SHORT, TP tight, SL 5x
    RR_orig = 5.0
    fee = 0.05 / 100
    
    def simulate(inverse=False):
        trades = []
        in_pos = False
        tp_price = 0; sl_price = 0; entry_p = 0
        for i in range(150, len(B)-1):
            if not in_pos:
                if sig[i] == 1:
                    in_pos = True
                    entry_p = opens[i+1]
                    wick_low = lows[i] * 0.999
                    dist = entry_p - wick_low
                    if dist <= 0 or (dist/entry_p) > 0.05:
                        in_pos = False
                        continue
                    
                    if not inverse:
                        # GỐC (LONG): Cố tình làm Win Rate CỰC THẤP bằng cách đặt TP siêu xa (R:R 1:5)
                        sl_price = wick_low
                        tp_price = entry_p + (RR_orig * dist)
                    else:
                        # ĐÁNH NGƯỢC (SHORT): TP ngắn, SL siêu xa (Đảo lộn lại)
                        tp_price = wick_low
                        sl_price = entry_p + (RR_orig * dist)
            else:
                if not inverse:
                    if lows[i] <= sl_price:
                        loss_pct = (sl_price - entry_p) / entry_p * 100
                        trades.append(loss_pct - fee*200)
                        in_pos = False
                    elif highs[i] >= tp_price:
                        win_pct = (tp_price - entry_p) / entry_p * 100
                        trades.append(win_pct - fee*200)
                        in_pos = False
                else:
                    # SHORT
                    if highs[i] >= sl_price:
                        loss_pct = (entry_p - sl_price) / entry_p * 100
                        trades.append(loss_pct - fee*200)
                        in_pos = False
                    elif lows[i] <= tp_price:
                        win_pct = (entry_p - tp_price) / entry_p * 100
                        trades.append(win_pct - fee*200)
                        in_pos = False
        return np.array(trades)

    tr_orig = simulate(inverse=False)
    tr_inv = simulate(inverse=True)
    
    def print_stats(name, tr):
        wr = (tr>0).mean()*100
        print(f"{name:20s} | Lệnh: {len(tr):4d} | Win Rate: {wr:5.1f}% | PnL Ròng: {tr.sum():6.2f}%")
        
    print("=== THÍ NGHIỆM ĐÁNH NGƯỢC (INVERSE FALLACY) ===")
    print_stats("Bản Gốc (LONG 1:5)", tr_orig)
    print_stats("Đánh Ngược (SHORT)", tr_inv)

run()
