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
    
    sl_pct = 3.0  # Sếp yêu cầu SL 3%
    tp_pct = 16.5
    cost = 2 * (0.0005 + 0.0001) * 100
    
    side = X.signals(B, h=8.0, mult=3.0, rsi_os=20, rsi_ob=80, vol_mult=2.5)
    c = B["close"].to_numpy()
    
    T = sim.run(B, side, c * sl_pct / 100, c * tp_pct / 100)
    T['pnl_pct'] = np.where(T['reason'] == 'TP', tp_pct - cost, -sl_pct - cost)
    T['r_val'] = T['pnl_pct'] / sl_pct
    
    trades = len(T)
    wins = len(T[T['reason'] == 'TP'])
    wr = (wins / trades) * 100 if trades > 0 else 0
    net_r = T['r_val'].sum()
    total_pnl = T['pnl_pct'].sum()
    
    # Mô phỏng Lãi kép với Risk = 1% vốn
    cap_1 = 10_000_000 # 10 Triệu
    peak_1 = cap_1
    mdd_1 = 0
    max_loss_streak = 0
    current_loss_streak = 0
    
    for _, row in T.iterrows():
        pct = row['r_val'] * 0.01 # Risk 1%
        
        if pct < 0:
            current_loss_streak += 1
            max_loss_streak = max(max_loss_streak, current_loss_streak)
        else:
            current_loss_streak = 0
            
        cap_1 = cap_1 * (1 + pct)
        peak_1 = max(peak_1, cap_1)
        dd = (cap_1 - peak_1) / peak_1
        mdd_1 = min(mdd_1, dd)

    print("\n[BÁO CÁO THỰC CHIẾN - XRP NADA VỚI CẮT LỖ RỘNG (SL 3.0%)]")
    print(f"- Cấu hình: RSI < 20, Vol > 2.5x | SL 3.0% | TP 16.5%")
    print(f"- Số lệnh: {trades} lệnh")
    print(f"- Tỷ lệ thắng (Win Rate): {wr:.1f}%")
    print(f"- Lãi Ròng gộp (Không đòn bẩy): +{total_pnl:.2f}%")
    print(f"- Tổng Lợi nhuận (R): {net_r:.2f} R")
    
    print(f"\n[MÔ PHỎNG LÃI KÉP (RISK 1% VỐN / LỆNH)]")
    print(f"- Vốn ban đầu: 10,000,000 VNĐ")
    print(f"- Vốn cuối kỳ (Sau 4 năm): {cap_1:,.0f} VNĐ")
    print(f"- Sụt giảm tối đa (Max Drawdown): {mdd_1*100:.1f}%")
    print(f"- Chuỗi thua liên tiếp: {max_loss_streak} lệnh")

run()
