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
    
    sl_pct = 0.55
    tp_pct = 16.5
    cost = 2 * (0.0005 + 0.0001) * 100
    
    side = X.signals(B, h=8.0, mult=3.0, rsi_os=20, rsi_ob=80, vol_mult=2.5)
    T = sim.run(B, side, c * sl_pct / 100, c * tp_pct / 100)
    
    T['pnl_pct'] = np.where(T['reason'] == 'TP', tp_pct - cost, -sl_pct - cost)
    T['r_val'] = T['pnl_pct'] / sl_pct
    
    # Kịch bản 1: Risk 1% (1 R = 1%)
    cap_1 = 10_000_000
    peak_1 = cap_1
    mdd_1 = 0
    
    # Kịch bản 2: Risk 3% (1 R = 2%)
    cap_2 = 10_000_000
    peak_2 = cap_2
    mdd_2 = 0
    
    for _, row in T.iterrows():
        r = row['r_val']
        
        # Risk 1%
        pct_1 = r * 0.01
        cap_1 = cap_1 * (1 + pct_1)
        peak_1 = max(peak_1, cap_1)
        dd_1 = (cap_1 - peak_1) / peak_1
        mdd_1 = min(mdd_1, dd_1)
        
        # Risk 3%
        pct_2 = r * 0.03
        cap_2 = cap_2 * (1 + pct_2)
        peak_2 = max(peak_2, cap_2)
        dd_2 = (cap_2 - peak_2) / peak_2
        mdd_2 = min(mdd_2, dd_2)

    print(f"\n[VỐN 10 TRIỆU ĐỒNG - SAU 4 NĂM]")
    print(f"KỊCH BẢN 1 (Risk 1% vốn / Lệnh):")
    print(f"- Số tiền cuối cùng: {cap_1:,.0f} VNĐ")
    print(f"- Sụt giảm tối đa (Max Drawdown): {mdd_1*100:.1f}%")
    
    print(f"\nKỊCH BẢN 2 (Risk 3% vốn / Lệnh):")
    print(f"- Số tiền cuối cùng: {cap_2:,.0f} VNĐ")
    print(f"- Sụt giảm tối đa (Max Drawdown): {mdd_2*100:.1f}%")

run()
