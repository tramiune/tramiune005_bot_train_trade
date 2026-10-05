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
    
    B = df.resample('5min').agg({
        'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
    }).dropna()
    
    c, h, l, v = B["close"], B["high"], B["low"], B["volume"]
    dts = B.index
    
    h_c = h - c.shift()
    l_c = l - c.shift()
    tr = pd.concat([h - l, h_c.abs(), l_c.abs()], axis=1).max(axis=1)
    
    a = tr.rolling(20).mean()
    mid = c.rolling(20).mean()
    sd = c.rolling(20).std()
    
    on = (mid + 2 * sd < mid + 1.5 * a) & (mid - 2 * sd > mid - 1.5 * a)
    dur = on.groupby((~on).cumsum()).cumsum()
    
    vol_mean = v.rolling(20).mean()
    fire = (~on) & on.shift(1, fill_value=False) & (dur.shift(1) >= 5) & (v > 1.5 * vol_mean)
    bull = c > mid
    
    # Tính EMA 1D và Khoảng cách (%)
    ema_1d = c.ewm(span=288, adjust=False).mean()
    dist_pct = ((c - ema_1d) / ema_1d).abs() * 100
    
    # Tính Khung giờ (UTC)
    hours = dts.hour
    
    # Tạo các bộ Tín hiệu (Tất cả là ĐÁNH THUẬN - FOLLOW)
    sig_base = np.where(fire, np.where(bull, 1, -1), 0)
    
    # Lọc 1: Gần Vạch Xuất Phát (Cách EMA 1D < 0.2%)
    sig_dist = np.where(fire & (dist_pct < 0.2), np.where(bull, 1, -1), 0)
    
    # Lọc 2: Gần Vạch Xuất Phát + Giờ Phiên Âu/Mỹ (7,8,9 UTC và 13,14,15,16,17 UTC)
    valid_hours = np.isin(hours, [7, 8, 9, 13, 14, 15, 16, 17])
    sig_combo = np.where(fire & (dist_pct < 0.2) & valid_hours, np.where(bull, 1, -1), 0)
    
    opens = B["open"].values
    highs = B["high"].values
    lows = B["low"].values
    
    tp_pct = 8.0
    sl_pct = 8.0
    fee = 0.05 / 100
    
    def backtest(signals):
        trades = []
        in_pos = False
        tp_price = 0; sl_price = 0; side = 0
        for i in range(288, len(B)-1):
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

    tr_base = backtest(sig_base)
    tr_dist = backtest(sig_dist)
    tr_combo = backtest(sig_combo)
    
    def print_stats(name, tr):
        if len(tr) == 0:
            print(f"{name:45s} | Không có lệnh")
            return
        wr = (tr>0).mean()*100
        print(f"{name:45s} | Số Lệnh: {len(tr):3d} | Win Rate: {wr:5.1f}% | PnL Ròng: {tr.sum():6.2f}%")

    print("\n=== KIỂM CHỨNG CHÉN THÁNH (SQUEEZE 5M FOLLOW - TP 8, SL 8) ===")
    print(f"Mốc Hòa Vốn (Bao gồm Phí Sàn 0.1%): 50.6%")
    print("-" * 80)
    print_stats("1. Bản Gốc (Thả rông)", tr_base)
    print_stats("2. Lọc Căn Cứ (Giá cách EMA 1D < 0.2%)", tr_dist)
    print_stats("3. Combo Hủy Diệt (Căn Cứ + Giờ Phiên Âu/Mỹ)", tr_combo)

run()
