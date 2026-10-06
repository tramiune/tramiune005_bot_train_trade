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
    
    B = H.resample(d1, 5)
    c = B["close"].to_numpy()
    
    # Cấu hình Vua 1 ăn 30
    sl_pct = 0.5
    tp_pct = 15.0
    r_os, v_mult, m = 20, 2.5, 3.0
    
    side = X.signals(B, h=8.0, mult=m, rsi_os=r_os, rsi_ob=100-r_os, vol_mult=v_mult)
    
    T = sim.run(B, side, c * sl_pct / 100, c * tp_pct / 100)
    
    # Analyze the 88 losing trades
    losses = T[T['reason'] == 'SL'].copy()
    
    print(f"\nPhân tích {len(losses)} lệnh THUA (Cắn SL {sl_pct}%):")
    
    mfes = []
    
    # Lặp qua từng lệnh thua để tìm giá cao nhất nó từng đạt được trước khi chết
    for idx, row in losses.iterrows():
        e_t = row['entry_t']
        ex_t = row['exit_t']
        entry_px = row['entry']
        
        # Tìm index trong mảng 1m
        j_start = np.searchsorted(sim.t, e_t)
        j_end = np.searchsorted(sim.t, ex_t)
        
        if j_start < j_end:
            max_high = np.max(sim.h[j_start:j_end])
            max_gain_pct = (max_high / entry_px - 1) * 100
        else:
            max_gain_pct = 0
            
        mfes.append(max_gain_pct)
        
    losses['mfe_pct'] = mfes
    
    print("\nThống kê MFE (Mức giá nảy lên cao nhất trước khi cắn SL):")
    print(f"- Lệnh cắm đầu chết luôn (MFE < 0.5%): {len(losses[losses['mfe_pct'] < 0.5])} lệnh")
    print(f"- Lệnh nảy lên được 0.5% - 2.0%: {len(losses[(losses['mfe_pct'] >= 0.5) & (losses['mfe_pct'] < 2.0)])} lệnh")
    print(f"- Lệnh nảy lên được 2.0% - 5.0%: {len(losses[(losses['mfe_pct'] >= 2.0) & (losses['mfe_pct'] < 5.0)])} lệnh")
    print(f"- Lệnh nảy lên được 5.0% - 10.0%: {len(losses[(losses['mfe_pct'] >= 5.0) & (losses['mfe_pct'] < 10.0)])} lệnh")
    print(f"- Lệnh nảy lên được > 10.0% (Suýt cắn TP 15%): {len(losses[losses['mfe_pct'] >= 10.0])} lệnh")
    
    # In ra 5 lệnh cay đắng nhất (Suýt ăn mà lại quay đầu chết)
    print("\nTop 5 lệnh 'Cay Đắng Nhất' (Nảy lên rất cao nhưng không chốt, sau đó quay đầu cắn SL):")
    bitter = losses.sort_values('mfe_pct', ascending=False).head(5)
    for idx, row in bitter.iterrows():
        entry_dt = pd.to_datetime(row['entry_t'], unit='s')
        print(f"- Ngày {entry_dt}: Mua giá {row['entry']:.4f} -> Nảy lên cao nhất +{row['mfe_pct']:.2f}% -> Rớt lại cắn SL -{sl_pct}%")

run()
