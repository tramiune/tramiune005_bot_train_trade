import sys, os
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.abspath(".agents/skills/honest-backtest/scripts"))
import bt_data
import bt_harness as H
from scratch_portfolio_unified import get_sol_trades

def run():
    T_sol = get_sol_trades()
    cap = 10_000_000
    peak = cap
    mdd = 0
    max_loss_streak = 0
    current_loss_streak = 0
    
    for i, row in T_sol.iterrows():
        pct = row['net_r'] * 0.15 # Risk 15%
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
        
    print(f"[MÔ PHỎNG LÃI KÉP - SOL CƯỠI SÓNG (RISK 15% VỐN)]")
    print(f"- Số lệnh: {len(T_sol)}")
    print(f"- Vốn ban đầu: 10,000,000 VNĐ")
    print(f"- Vốn cuối kỳ (Sau 4 năm): {cap:,.0f} VNĐ")
    print(f"- Hệ số nhân: x{cap/10_000_000:,.1f} lần")
    print(f"- Max Drawdown: {mdd*100:.1f}%")
    print(f"- Chuỗi thua liên tiếp: {max_loss_streak} lệnh")

run()
