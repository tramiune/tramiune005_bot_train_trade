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
    
    RSI_LIST = [15, 20, 25]
    VOL_LIST = [1.5, 2.0, 2.5, 3.0]
    BAND_LIST = [2.5, 3.0, 3.5]
    SL_LIST = [0.5, 0.75, 1.0, 1.5, 2.0]
    RR_LIST = [5, 8, 10, 12, 15, 20]
    
    total_runs = len(RSI_LIST) * len(VOL_LIST) * len(BAND_LIST) * len(SL_LIST) * len(RR_LIST)
    print(f"Bắt đầu Quét Đa Chiều (Mega Grid Search) với {total_runs} kịch bản...")
    
    start_time = time.time()
    rows = []
    
    for r_os, v_mult, m in itertools.product(RSI_LIST, VOL_LIST, BAND_LIST):
        # Generate signal once for this entry config
        side = X.signals(B, h=8.0, mult=m, rsi_os=r_os, rsi_ob=100-r_os, vol_mult=v_mult)
        
        # Bỏ qua nếu có quá ít tín hiệu
        if (side == 1).sum() < 20:
            continue
            
        # For this signal, run all SL and RR combos
        for sl, rr in itertools.product(SL_LIST, RR_LIST):
            tp = sl * rr
            T = sim.run(B, side, c * sl / 100, c * tp / 100)
            
            if len(T) < 20:
                continue
                
            wins = int((T.reason == "TP").sum())
            losses = len(T) - wins
            wr = (wins / len(T)) * 100
            
            win_pct = tp - cost
            loss_pct = -sl - cost
            sum_pct = (wins * win_pct) + (losses * loss_pct)
            sum_R = sum_pct / sl
            
            # Tính Expectancy (EV) theo R
            ev_R = sum_R / len(T) if len(T) > 0 else 0
            
            rows.append({
                "RSI": r_os, "Vol": v_mult, "Band": m, "SL%": sl, "TP%": tp, "RR": rr,
                "Trades": len(T), "Wins": wins, "WinRate": wr, "Net_R": sum_R, "EV_R": ev_R
            })
            
    end_time = time.time()
    print(f"\nHoàn thành quét trong {end_time - start_time:.1f} giây!")
    
    R_df = pd.DataFrame(rows)
    if len(R_df) > 0:
        R_df = R_df.sort_values("Net_R", ascending=False).head(20)
        print("\n=== TOP 20 CẤU HÌNH XRP (KẾT HỢP ENTRY + EXIT) LÃI NHẤT LỊCH SỬ ===")
        print(R_df.round(2).to_string(index=False))
        
        # Save to artifact for user to see
        out_path = '/Users/finn/.gemini/antigravity/brain/921139ef-edbf-43e7-bf4e-d052df21201b/xrp_mega_grid.md'
        md = f"# TỔNG KIỂM TRA ĐA CHIỀU (MEGA GRID SEARCH) XRP 5M\n\n"
        md += f"Đã quét tổng cộng **{total_runs} kịch bản** kết hợp giữa Bộ Lọc Vào Lệnh (RSI, Volume, Band) và Bộ Quản Trị Vốn (SL, TP).\n\n"
        md += "### BẢNG XẾP HẠNG TOP 20 CẤU HÌNH SINH LỜI KHỦNG NHẤT (Xếp theo Net R)\n\n"
        md += "| Xếp Hạng | RSI | Volume | Band | SL (%) | TP (%) | Tỷ Lệ (RR) | Số Lệnh | Win Rate | Lãi Ròng (Net R) | Lãi Ròng (Thuần %) |\n"
        md += "|---|---|---|---|---|---|---|---|---|---|---|\n"
        for i, (_, row) in enumerate(R_df.iterrows()):
            raw_pct = row['Net_R'] * row['SL%']
            md += f"| Top {i+1} | < {row['RSI']} | > {row['Vol']}x | {row['Band']} | {row['SL%']}% | {row['TP%']}% | 1 ăn {int(row['RR'])} | {int(row['Trades'])} | {row['WinRate']:.1f}% | **+{row['Net_R']:.1f} R** | +{raw_pct:.1f}% |\n"
        with open(out_path, 'w') as f:
            f.write(md)
    else:
        print("Không tìm thấy cấu hình nào hợp lệ.")

run()
