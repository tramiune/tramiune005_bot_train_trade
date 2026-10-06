import sys, os
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.abspath(".agents/skills/honest-backtest/scripts"))
import bt_data
import bt_harness as H
import xrp_nada as X

def run():
    print("Loading XRPUSDT 1m data...")
    d1 = bt_data.load("XRPUSDT", "1m")
    sim = H.Sim(d1)
    
    print("Resampling to 5m & Extracting Signals...")
    B = H.resample(d1, 5)
    c = B["close"].to_numpy()
    
    # Giữ nguyên Cấu hình Nhập Lệnh Siêu Việt
    r_os, v_mult, m = 20, 2.5, 3.0
    side = X.signals(B, h=8.0, mult=m, rsi_os=r_os, rsi_ob=100-r_os, vol_mult=v_mult)
    
    cost = 2 * (0.0005 + 0.0001) * 100 # 0.12%
    
    # Quét độ phân giải cao cho Cắt Lỗ
    SL_LIST = [0.50, 0.55, 0.60, 0.65, 0.70, 0.75]
    RR_LIST = [20, 25, 30, 35]
    
    print(f"\nBắt đầu nội suy Cắt Lỗ (SL) với độ phân giải 0.05%...")
    rows = []
    
    for sl in SL_LIST:
        for rr in RR_LIST:
            tp = sl * rr
            T = sim.run(B, side, c * sl / 100, c * tp / 100)
            
            if len(T) < 10:
                continue
                
            wins = int((T.reason == "TP").sum())
            losses = len(T) - wins
            wr = (wins / len(T)) * 100
            
            win_pct = tp - cost
            loss_pct = -sl - cost
            sum_pct = (wins * win_pct) + (losses * loss_pct)
            sum_R = sum_pct / sl
            
            rows.append({
                "SL%": sl, "TP%": tp, "RR": rr,
                "Trades": len(T), "Wins": wins, "WinRate": wr, "Net_R": sum_R
            })
            
    R_df = pd.DataFrame(rows)
    if len(R_df) > 0:
        R_df = R_df.sort_values("Net_R", ascending=False).head(15)
        print("\n=== TOP 15 CẤU HÌNH SL & RR CHI TIẾT NHẤT ===")
        print(R_df.round(2).to_string(index=False))
        
        # In ra riêng sự khác biệt của SL (Cố định RR 30)
        print("\n=== SO SÁNH TRỰC TIẾP TẠI MỨC RR 30 ===")
        rr30 = R_df[R_df['RR'] == 30].sort_values("SL%")
        print(rr30.round(2).to_string(index=False))
    else:
        print("Không tìm thấy dữ liệu hợp lệ.")

run()
