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

def run():
    print("Loading XRPUSDT 1m data...")
    d1 = bt_data.load("XRPUSDT", "1m")
    sim = H.Sim(d1)
    
    print("Resampling to 5m...")
    B = H.resample(d1, 5)
    c = B["close"].to_numpy()
    
    cost = 2 * (0.0005 + 0.0001) * 100 # 0.12% round trip
    
    # Ultra-Fine Grid
    RSI_LIST = [5, 10, 15, 18, 20, 22, 25, 30]
    VOL_LIST = [1.5, 2.0, 2.5, 3.0, 3.5, 4.0]
    BAND_LIST = [2.5, 3.0, 3.5, 4.0]
    SL_LIST = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]
    RR_LIST = [5, 8, 10, 12, 15, 20]
    
    total_entry = len(RSI_LIST) * len(VOL_LIST) * len(BAND_LIST)
    total_exit = len(SL_LIST) * len(RR_LIST)
    total_runs = total_entry * total_exit
    print(f"Bắt đầu Quét Đa Chiều (ULTRA Grid Search) với {total_runs} kịch bản...")
    
    start_time = time.time()
    rows = []
    
    for r_os, v_mult, m in itertools.product(RSI_LIST, VOL_LIST, BAND_LIST):
        # Generate signal once for this entry config
        side = X.signals(B, h=8.0, mult=m, rsi_os=r_os, rsi_ob=100-r_os, vol_mult=v_mult)
        
        if (side == 1).sum() < 15:
            continue
            
        for sl, rr in itertools.product(SL_LIST, RR_LIST):
            tp = sl * rr
            T = sim.run(B, side, c * sl / 100, c * tp / 100)
            
            if len(T) < 15:
                continue
                
            wins = int((T.reason == "TP").sum())
            losses = len(T) - wins
            wr = (wins / len(T)) * 100
            
            win_pct = tp - cost
            loss_pct = -sl - cost
            sum_pct = (wins * win_pct) + (losses * loss_pct)
            sum_R = sum_pct / sl
            
            ev_R = sum_R / len(T) if len(T) > 0 else 0
            
            rows.append({
                "RSI": r_os, "Vol": v_mult, "Band": m, "SL%": sl, "TP%": tp, "RR": rr,
                "Trades": len(T), "Wins": wins, "WinRate": wr, "Net_R": sum_R, "EV_R": ev_R
            })
            
    end_time = time.time()
    print(f"\nHoàn thành quét siêu tốc trong {end_time - start_time:.1f} giây!")
    
    R_df = pd.DataFrame(rows)
    if len(R_df) > 0:
        R_df = R_df.sort_values("Net_R", ascending=False).head(20)
        print("\n=== TOP 20 CẤU HÌNH XRP (ULTRA GRID) LÃI NHẤT LỊCH SỬ ===")
        print(R_df.round(2).to_string(index=False))
        
        # Save to artifact
        out_path = '/Users/finn/.gemini/antigravity/brain/921139ef-edbf-43e7-bf4e-d052df21201b/xrp_ultra_grid.md'
        md = f"# SIÊU QUÉT ĐA CHIỀU (ULTRA GRID SEARCH) XRP 5M\n\n"
        md += f"Đã quét tổng cộng **{total_runs} kịch bản** (Khám phá tận cùng mọi ngóc ngách của thuật toán Nadaraya-Watson).\n\n"
        md += "### BẢNG XẾP HẠNG TOP 20 CẤU HÌNH VÀNG\n\n"
        md += "| Xếp Hạng | RSI | Volume | Band | SL (%) | TP (%) | Tỷ Lệ (RR) | Số Lệnh | Win Rate | Lãi Ròng (Net R) | Ký Vọng (EV/Lệnh) |\n"
        md += "|---|---|---|---|---|---|---|---|---|---|---|\n"
        for i, (_, row) in enumerate(R_df.iterrows()):
            md += f"| Top {i+1} | < {row['RSI']} | > {row['Vol']}x | {row['Band']} | {row['SL%']}% | {row['TP%']}% | 1 ăn {int(row['RR'])} | {int(row['Trades'])} | {row['WinRate']:.1f}% | **+{row['Net_R']:.1f} R** | +{row['EV_R']:.2f} R |\n"
        with open(out_path, 'w') as f:
            f.write(md)
        print(f"Đã xuất File Artifact: {out_path}")
    else:
        print("Không tìm thấy cấu hình nào hợp lệ.")

run()
