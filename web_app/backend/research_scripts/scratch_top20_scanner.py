import itertools
import os
import sys
import numpy as np
import pandas as pd
import time

sys.path.insert(0, os.path.abspath(".agents/skills/honest-backtest/scripts"))
import bt_data
import bt_harness as H
import xrp_nada as X

COINS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "AVAXUSDT",
    "LINKUSDT", "MATICUSDT", "DOTUSDT", "LTCUSDT", "BCHUSDT",
    "ATOMUSDT", "UNIUSDT", "FTMUSDT", "NEARUSDT", "ALGOUSDT",
    "SANDUSDT", "MANAUSDT", "AXSUSDT", "GALAUSDT", "FILUSDT"
]

def scan_coin(symbol):
    print(f"\n[{symbol}] Đang tải dữ liệu 4 năm (1m)...")
    try:
        d1 = bt_data.load(symbol, "1m")
    except Exception as e:
        print(f"[{symbol}] Lỗi tải dữ liệu: {e}")
        return None
        
    sim = H.Sim(d1)
    B = H.resample(d1, 5)
    c = B["close"].to_numpy()
    cost = 2 * (0.0005 + 0.0001) * 100 
    
    RSI_LIST = [15, 20, 25]
    VOL_LIST = [1.5, 2.0, 3.0]
    BAND_LIST = [2.5, 3.0, 3.5]
    SL_LIST = [0.75, 1.0, 1.5, 2.0]
    RR_LIST = [5, 10, 15, 20]
    
    rows = []
    print(f"[{symbol}] Đang quét 432 cấu hình...")
    
    for r_os, v_mult, m in itertools.product(RSI_LIST, VOL_LIST, BAND_LIST):
        side = X.signals(B, h=8.0, mult=m, rsi_os=r_os, rsi_ob=100-r_os, vol_mult=v_mult)
        if (side == 1).sum() < 20: continue
            
        for sl, rr in itertools.product(SL_LIST, RR_LIST):
            tp = sl * rr
            T = sim.run(B, side, c * sl / 100, c * tp / 100)
            if len(T) < 20: continue
                
            wins = int((T.reason == "TP").sum())
            losses = len(T) - wins
            if len(T) > 0:
                wr = (wins / len(T)) * 100
                sum_pct = (wins * (tp - cost)) + (losses * (-sl - cost))
                sum_R = sum_pct / sl
                
                rows.append({
                    "RSI": r_os, "Vol": v_mult, "Band": m, "SL": sl, "TP": tp, "RR": rr,
                    "Trades": len(T), "Wins": wins, "WinRate": wr, "Net_R": sum_R
                })
                
    if not rows:
        return None
        
    R_df = pd.DataFrame(rows)
    best = R_df.sort_values("Net_R", ascending=False).iloc[0]
    return best

def run():
    out_path = '/Users/finn/.gemini/antigravity/brain/921139ef-edbf-43e7-bf4e-d052df21201b/top20_coins_optimal.md'
    
    md = f"# HỒ SƠ TỐI ƯU HÓA 20 ĐỒNG COIN (MEGA SCAN)\n\n"
    md += f"Báo cáo này chứa Cấu hình Tối ưu Nhất (Global Optimum) cho từng đồng coin, dựa trên bộ lọc Nadaraya-Watson.\n\n"
    md += "| Coin | RSI | Volume | Band | SL (%) | TP (%) | Tỷ Lệ (RR) | Số Lệnh | Win Rate | Lãi Ròng (Net R) |\n"
    md += "|---|---|---|---|---|---|---|---|---|---|\n"
    
    with open(out_path, 'w') as f:
        f.write(md)
        
    for symbol in COINS:
        best = scan_coin(symbol)
        if best is not None:
            line = f"| **{symbol}** | < {int(best['RSI'])} | > {best['Vol']}x | {best['Band']} | {best['SL']}% | {best['TP']}% | 1 ăn {int(best['RR'])} | {int(best['Trades'])} | {best['WinRate']:.1f}% | **{best['Net_R']:+.1f} R** |\n"
        else:
            line = f"| **{symbol}** | - | - | - | - | - | - | - | - | <span style='color:red'>Không có cấu hình Lãi</span> |\n"
            
        with open(out_path, 'a') as f:
            f.write(line)
        print(line.strip())

run()
