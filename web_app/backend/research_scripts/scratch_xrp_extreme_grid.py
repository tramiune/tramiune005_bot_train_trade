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
    cost = 2 * (0.0005 + 0.0001) * 100
    
    # Cấu hình Cực độ (Extreme)
    RSI_LIST = [15, 20] 
    VOL_LIST = [2.5, 3.0, 4.0, 5.0] # Volume sâu hơn
    BAND_LIST = [3.0, 3.5, 4.0, 4.5] # Dải lệch sâu hơn
    SL_LIST = [0.2, 0.3, 0.4, 0.5, 0.75] # Cắt lỗ siêu nhỏ
    RR_LIST = [10, 15, 20, 25, 30] # RR cao để gánh
    
    print(f"Bắt đầu Quét Cấu hình CỰC ĐOAN (Extreme Grid Search)...")
    start_time = time.time()
    rows = []
    
    for r_os, v_mult, m in itertools.product(RSI_LIST, VOL_LIST, BAND_LIST):
        side = X.signals(B, h=8.0, mult=m, rsi_os=r_os, rsi_ob=100-r_os, vol_mult=v_mult)
        if (side == 1).sum() < 10:
            continue
            
        for sl, rr in itertools.product(SL_LIST, RR_LIST):
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
            
            ev_R = sum_R / len(T) if len(T) > 0 else 0
            
            rows.append({
                "RSI": r_os, "Vol": v_mult, "Band": m, "SL%": sl, "TP%": tp, "RR": rr,
                "Trades": len(T), "Wins": wins, "WinRate": wr, "Net_R": sum_R, "EV_R": ev_R
            })
            
    end_time = time.time()
    print(f"\nHoàn thành trong {end_time - start_time:.1f} giây!")
    
    R_df = pd.DataFrame(rows)
    if len(R_df) > 0:
        R_df = R_df.sort_values("Net_R", ascending=False).head(20)
        print("\n=== TOP 20 CẤU HÌNH XRP CỰC ĐOAN LÃI NHẤT ===")
        print(R_df.round(2).to_string(index=False))
    else:
        print("Không tìm thấy cấu hình cực đoan nào có lãi.")

run()
