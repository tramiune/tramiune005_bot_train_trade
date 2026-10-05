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
    
    c, h, l, v = B["close"], B["high"], B["low"], B["volume"]
    
    h_c = h - c.shift()
    l_c = l - c.shift()
    tr = pd.concat([h - l, h_c.abs(), l_c.abs()], axis=1).max(axis=1)
    
    a = tr.rolling(20).mean()
    mid = c.rolling(20).mean()
    sd = c.rolling(20).std()
    
    on = (mid + 2 * sd < mid + 1.5 * a) & (mid - 2 * sd > mid - 1.5 * a)
    dur = on.groupby((~on).cumsum()).cumsum()
    fire = (~on) & on.shift(1, fill_value=False) & (dur.shift(1) >= 5) & (v > 1.5 * v.rolling(20).mean())
    bull = c > mid
    
    sig_follow = np.where(fire, np.where(bull, 1, -1), 0)
    
    # FILTER 1: HTF Trend (4h EMA 20 = 15m EMA 320)
    ema_320 = c.ewm(span=320, adjust=False).mean()
    htf_bull = c > ema_320
    
    # FILTER 2: Volume threshold (v > 2.5x instead of 1.5x)
    super_vol = v > 2.5 * v.rolling(20).mean()
    
    opens = B["open"].values
    highs = B["high"].values
    lows = B["low"].values
    dts = B.index
    
    tp_pct = 5.0
    sl_pct = 2.0
    fee = 0.05 / 100
    
    def simulate(signals):
        trades = []
        in_pos = False
        tp_price = 0; sl_price = 0; side = 0
        for i in range(320, len(B)-1):
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
        return np.array(trades)

    # Base
    tr_base = simulate(sig_follow)
    
    # With HTF Filter
    sig_htf = np.where((sig_follow == 1) & htf_bull, 1, np.where((sig_follow == -1) & ~htf_bull, -1, 0))
    tr_htf = simulate(sig_htf)
    
    # With Super Vol Filter
    sig_vol = np.where((sig_follow != 0) & super_vol, sig_follow, 0)
    tr_vol = simulate(sig_vol)
    
    def print_res(name, tr):
        wr = (tr>0).mean()*100
        print(f"{name:15s} | Lệnh: {len(tr):3d} | Win Rate: {wr:5.1f}% | PnL: {tr.sum():6.2f}%")
        
    print("=== FILTER COMPARISON (TP 5%, SL 2%) ===")
    print_res("Gốc (Không lọc)", tr_base)
    print_res("Lọc Trend 4H", tr_htf)
    print_res("Lọc Super Vol", tr_vol)

run()
