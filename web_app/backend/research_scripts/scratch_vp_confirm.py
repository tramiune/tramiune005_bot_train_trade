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
    
    c, h, l, v = B["close"].values, B["high"].values, B["low"].values, B["volume"].values
    opens = B["open"].values
    dts = B.index
    
    window = 200
    prices = (h + l + c) / 3
    pocs = np.zeros(len(B))
    
    for i in range(window, len(B)):
        p = prices[i-window:i]
        vol = v[i-window:i]
        hist, bins = np.histogram(p, bins=20, weights=vol)
        pocs[i] = (bins[np.argmax(hist)] + bins[np.argmax(hist)+1]) / 2
        
    ema_1d = B["close"].ewm(span=1920, adjust=False).mean().values
    
    def simulate(use_confirmation=False):
        trades = []
        in_pos = False
        tp_price = 0; sl_price = 0; entry_p = 0
        fee = 0.05 / 100
        RR = 2.0
        
        for i in range(window, len(B)-1):
            if not in_pos:
                if pocs[i] > 0 and c[i] > ema_1d[i]:
                    if c[i-1] > pocs[i] * 1.005 and l[i] <= pocs[i]:
                        
                        valid = True
                        if use_confirmation:
                            # Điều kiện xác nhận: 
                            # 1. Phải đóng cửa trên POC (Rút râu thành công)
                            # 2. Phải là nến xanh (c > o) HOẶC râu dưới rất dài (close_pos > 0.6)
                            crange = h[i] - l[i]
                            if crange == 0: valid = False
                            else:
                                close_pos = (c[i] - l[i]) / crange
                                if c[i] < pocs[i] or (c[i] <= opens[i] and close_pos < 0.6):
                                    valid = False
                                    
                        if valid:
                            in_pos = True
                            entry_p = opens[i+1]
                            sl_price = entry_p * 0.98
                            dist = entry_p - sl_price
                            tp_price = entry_p + (RR * dist)
            else:
                if lows[i] <= sl_price:
                    trades.append(-2.0 - fee*200)
                    in_pos = False
                elif highs[i] >= tp_price:
                    trades.append(4.0 - fee*200)
                    in_pos = False
        return np.array(trades)

    lows = l; highs = h
    tr_blind = simulate(use_confirmation=False)
    tr_conf = simulate(use_confirmation=True)
    
    def print_stats(name, tr):
        wr = (tr>0).mean()*100
        print(f"{name:30s} | Lệnh: {len(tr):4d} | Win Rate: {wr:5.1f}% | PnL Ròng: {tr.sum():6.2f}%")
        
    print("=== THÍ NGHIỆM: CÓ CẦN NẾN XÁC NHẬN KHI CHẠM POC? ===")
    print_stats("Bắt Mù (Chạm là Múc)", tr_blind)
    print_stats("Đợi Nến Xác Nhận (Xanh/Rút râu)", tr_conf)

run()
