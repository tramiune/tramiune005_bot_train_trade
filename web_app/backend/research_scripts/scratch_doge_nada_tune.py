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
    print("Loading DOGEUSDT 1m data...")
    d1 = bt_data.load("DOGEUSDT", "1m")
    sim = H.Sim(d1)
    
    print("Resampling to 5m...")
    B = H.resample(d1, 5)
    c = B["close"].to_numpy()
    
    # Cố định SL 1.0% và TP 5.0% (RR 5) hoặc TP 10.0% (RR 10)
    sl = 1.5
    tp = 7.5 # RR 5
    cost = 2 * (0.0005 + 0.0001) * 100
    
    RSI_OS_LIST = [10, 15, 20, 25]
    VOL_MULT_LIST = [1.5, 2.0, 3.0, 4.0]
    MULT_LIST = [3.0, 4.0, 5.0]
    
    print(f"\nQuét cấu hình Entry cho DOGE (SL {sl}%, TP {tp}%):")
    rows = []
    
    for r_os, v_mult, m in itertools.product(RSI_OS_LIST, VOL_MULT_LIST, MULT_LIST):
        # Extract signals with custom parameters
        side = X.signals(B, h=8.0, mult=m, rsi_os=r_os, rsi_ob=100-r_os, vol_mult=v_mult)
        
        # We only care about BUY signals for catching bottoms
        # (Wait, X.signals generates both buy and sell. The backtester will execute both.)
        # Let's just run it:
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
            "RSI": r_os, "Vol": v_mult, "Band_Mult": m,
            "Trades": len(T), "WinRate": wr, "Net_R": sum_R
        })
        
    R_df = pd.DataFrame(rows)
    if len(R_df) > 0:
        R_df = R_df.sort_values("Net_R", ascending=False).head(10)
        print("\n--- TOP 10 CẤU HÌNH ENTRY TỐT NHẤT CHO DOGE ---")
        print(R_df.round(2).to_string(index=False))
    else:
        print("Không tìm thấy cấu hình nào có đủ >10 lệnh.")

run()
