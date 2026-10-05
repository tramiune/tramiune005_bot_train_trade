import itertools
import os
import sys
import numpy as np
import pandas as pd

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
    
    # Golden RR config cho XRP: Cắt lỗ 1%, Chốt lời 10%
    sl = 1.0
    tp = 10.0 
    cost = 2 * (0.0005 + 0.0001) * 100
    
    RSI_OS_LIST = [15, 20, 25, 30]
    VOL_MULT_LIST = [1.0, 1.5, 2.0, 2.5, 3.0]
    MULT_LIST = [2.5, 3.0, 3.5]
    
    print(f"\nQuét cấu hình tối ưu siêu cấp cho XRP (SL {sl}%, TP {tp}%):")
    rows = []
    
    for r_os, v_mult, m in itertools.product(RSI_OS_LIST, VOL_MULT_LIST, MULT_LIST):
        side = X.signals(B, h=8.0, mult=m, rsi_os=r_os, rsi_ob=100-r_os, vol_mult=v_mult)
        
        T = sim.run(B, side, c * sl / 100, c * tp / 100)
        
        if len(T) < 20: # Phải có ít nhất 20 lệnh trong 4 năm mới đáng tin cậy
            continue
            
        wins = int((T.reason == "TP").sum())
        losses = len(T) - wins
        wr = (wins / len(T)) * 100
        
        win_pct = tp - cost
        loss_pct = -sl - cost
        sum_pct = (wins * win_pct) + (losses * loss_pct)
        sum_R = sum_pct / sl
        
        rows.append({
            "RSI": r_os, "Vol": v_mult, "Band_Mult": m,
            "Trades": len(T), "Wins": wins, "WinRate": wr, "Net_R": sum_R
        })
        
    R_df = pd.DataFrame(rows)
    if len(R_df) > 0:
        R_df = R_df.sort_values("Net_R", ascending=False).head(10)
        print("\n--- TOP 10 CẤU HÌNH XRP TỐT NHẤT LỊCH SỬ ---")
        print(R_df.round(2).to_string(index=False))
    else:
        print("Không tìm thấy cấu hình nào có đủ >20 lệnh.")

run()
