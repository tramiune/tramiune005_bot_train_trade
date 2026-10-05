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
    
    c, h, l, o, v = B["close"], B["high"], B["low"], B["open"], B["volume"]
    
    support = l.shift(5).rolling(100).min()
    pierce = (l < support) & (l >= support * 0.98) & (c > support)
    candle_range = h - l
    close_pos = (c - l) / candle_range.replace(0, np.nan)
    fire_base = pierce & (close_pos > 0.5)
    
    # --- BỘ LỌC TỐI ƯU HÓA ---
    # 1. Trend Filter: Giá phải nằm trên đường EMA 4H (Khoảng 16 nến 15m) hoặc EMA 1D (96 nến 15m).
    # Chúng ta dùng EMA 1D (EMA 20 của khung 1 Ngày = 96 * 20 = 1920 nến 15m) để đảm bảo Uptrend vĩ mô.
    ema_1d = c.ewm(span=1920, adjust=False).mean()
    trend_bull = c > ema_1d
    
    # 2. Volume Filter: Nến quét đáy phải có Volume nổ mạnh (Ép bán tháo / Gom hàng)
    vol_ma = v.rolling(50).mean()
    high_vol = v > 1.5 * vol_ma
    
    fire_opt = fire_base & trend_bull & high_vol
    
    sig_base = np.where(fire_base, 1, 0)
    sig_opt = np.where(fire_opt, 1, 0)
    
    opens, highs, lows, dts = B["open"].values, B["high"].values, B["low"].values, B.index
    
    RR = 2.0
    fee = 0.05 / 100
    
    def simulate(signals, use_buffer=False):
        trades = []
        in_pos = False
        tp_price = 0; sl_price = 0; entry_p = 0
        for i in range(1920, len(B)-1):
            if not in_pos:
                if signals[i] == 1:
                    in_pos = True
                    entry_p = opens[i+1]
                    
                    # 3. Stop Loss Buffer: Đặt xa hơn một chút để né Double Sweep (Né râu)
                    if use_buffer:
                        sl_price = lows[i] * 0.995 # Đệm 0.5% dưới râu
                    else:
                        sl_price = lows[i] * 0.999 # Sát râu như cũ
                        
                    risk = entry_p - sl_price
                    if risk <= 0 or (risk/entry_p) > 0.05:
                        in_pos = False
                        continue
                    tp_price = entry_p + (RR * risk)
            else:
                if lows[i] <= sl_price:
                    loss_pct = (sl_price - entry_p) / entry_p * 100
                    trades.append(loss_pct - fee*200)
                    in_pos = False
                elif highs[i] >= tp_price:
                    win_pct = (tp_price - entry_p) / entry_p * 100
                    trades.append(win_pct - fee*200)
                    in_pos = False
        return np.array(trades)

    tr_base = simulate(sig_base, use_buffer=False)
    tr_opt1 = simulate(sig_opt, use_buffer=False)
    tr_opt2 = simulate(sig_opt, use_buffer=True)
    
    def print_res(name, tr):
        wr = (tr>0).mean()*100
        print(f"{name:30s} | Lệnh: {len(tr):4d} | Win Rate: {wr:5.1f}% | Lãi Ròng: {tr.sum():6.2f}%")
        
    print("=== GIẢI CỨU MÔ HÌNH QUÉT ĐÁY (R:R 1 ăn 2) ===")
    print_res("1. Gốc (Bắt dao rơi vô tội vạ)", tr_base)
    print_res("2. Lọc Trend 1D + Volume Nổ", tr_opt1)
    print_res("3. Lọc Trend + Nới Stoploss 0.5%", tr_opt2)

run()
