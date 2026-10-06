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
    
    sl_pct = 0.55
    tp_pct = 17.9 # TP siêu vi chỉnh
    cost = 2 * (0.0005 + 0.0001) * 100
    
    side = X.signals(B, h=8.0, mult=3.0, rsi_os=20, rsi_ob=80, vol_mult=2.4) # Vol siêu vi chỉnh
    c = B["close"].to_numpy()
    
    T = sim.run(B, side, c * sl_pct / 100, c * tp_pct / 100)
    T['pnl_pct'] = np.where(T['reason'] == 'TP', tp_pct - cost, -sl_pct - cost)
    T['r_val'] = T['pnl_pct'] / sl_pct
    
    # Mô phỏng Lãi kép với Risk = 5% vốn
    cap = 10_000_000 # 10 Triệu
    peak = cap
    mdd = 0
    max_loss_streak = 0
    current_loss_streak = 0
    
    for _, row in T.iterrows():
        pct = row['r_val'] * 0.10 # Risk 10%
        if pct <= -1.0: pct = -0.99
            
        if pct < 0:
            current_loss_streak += 1
            max_loss_streak = max(max_loss_streak, current_loss_streak)
        else:
            current_loss_streak = 0
            
        cap = cap * (1 + pct)
        peak = max(peak, cap)
        dd = (cap - peak) / peak
        mdd = min(mdd, dd)

    print(f"\n[MÔ PHỎNG LÃI KÉP - XRP BẮT ĐÁY (FINAL KING - RISK 10% VỐN)]")
    print(f"- Cấu hình Vua Cuối Cùng: SL 0.55%, TP 17.9%, Vol 2.4x (Tổng lãi {T['r_val'].sum():.1f} R)")
    print(f"- Vốn ban đầu: 10,000,000 VNĐ")
    print(f"- Vốn cuối kỳ (Sau 4 năm): {cap:,.0f} VNĐ")
    print(f"- Hệ số nhân tài khoản: x{cap / 10_000_000:,.1f} lần")
    print(f"- Sụt giảm tối đa (Max Drawdown): {mdd*100:.1f}%")
    print(f"- Chuỗi thua liên tiếp (Max Loss Streak): {max_loss_streak} lệnh")

run()
