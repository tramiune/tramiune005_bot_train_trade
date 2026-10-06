import sys, os
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.abspath(".agents/skills/honest-backtest/scripts"))
import bt_data
import bt_harness as H

def supertrend(h, l, c, period=17, mult=4.3):
    tr1 = h - l
    tr2 = np.abs(h - np.roll(c, 1))
    tr3 = np.abs(l - np.roll(c, 1))
    tr = np.maximum(tr1, np.maximum(tr2, tr3))
    tr[0] = tr1[0]
    
    atr = np.zeros(len(c))
    atr[0] = tr[0]
    for i in range(1, len(c)):
        atr[i] = (atr[i-1] * (period - 1) + tr[i]) / period
        
    hl2 = (h + l) / 2
    basic_ub = hl2 + mult * atr
    basic_lb = hl2 - mult * atr
    
    final_ub = np.zeros(len(c))
    final_lb = np.zeros(len(c))
    trend = np.ones(len(c))
    
    for i in range(1, len(c)):
        if basic_ub[i] < final_ub[i-1] or c[i-1] > final_ub[i-1]: final_ub[i] = basic_ub[i]
        else: final_ub[i] = final_ub[i-1]
            
        if basic_lb[i] > final_lb[i-1] or c[i-1] < final_lb[i-1]: final_lb[i] = basic_lb[i]
        else: final_lb[i] = final_lb[i-1]
            
        if trend[i-1] == 1 and c[i] < final_lb[i]: trend[i] = -1
        elif trend[i-1] == -1 and c[i] > final_ub[i]: trend[i] = 1
        else: trend[i] = trend[i-1]
    return trend

def run():
    print("Loading SOLUSDT 1m data...")
    sol = bt_data.load("SOLUSDT", "1m")
    sim = H.Sim(sol)
    B = H.resample(sol, 240) # 4H
    c = B["close"].to_numpy()
    h = B["high"].to_numpy()
    l = B["low"].to_numpy()
    
    trend = supertrend(h, l, c, 17, 4.3)
    side = np.zeros(len(B), dtype=int)
    for i in range(1, len(trend)):
        if trend[i] == 1 and trend[i-1] == -1: side[i] = 1
        elif trend[i] == -1 and trend[i-1] == 1: side[i] = -1
            
    ct = B["close_time"].to_numpy()
    idx = np.nonzero(side)[0]
    trades, pos, e = [], 0, 0.0
    for bi in idx:
        s = int(side[bi])
        j = np.searchsorted(sim.t, ct[bi])
        if j >= sim.n or sim.t[j] != ct[bi]: continue
        px = sim.o[j]
        if pos != 0:
            gross = pos * (px / e - 1) * 100
            trades.append({'gross': gross})
        pos, e = s, px
        
    T = pd.DataFrame(trades)
    cost = 0.12
    T['pnl'] = T['gross'] - cost
    avg_loss = abs(T[T['pnl'] < 0]['pnl'].mean())
    T['r_val'] = T['pnl'] / avg_loss
    
    # Mô phỏng Lãi kép với Risk = 10%
    cap_10 = 10_000_000 # 10 Triệu
    peak_10 = cap_10
    mdd_10 = 0
    max_loss_streak = 0
    current_loss_streak = 0
    
    for _, row in T.iterrows():
        r = row['r_val']
        pct = r * 0.10 # Risk 10% 
        
        if pct < 0:
            current_loss_streak += 1
            max_loss_streak = max(max_loss_streak, current_loss_streak)
        else:
            current_loss_streak = 0
            
        cap_10 = cap_10 * (1 + pct)
        peak_10 = max(peak_10, cap_10)
        dd = (cap_10 - peak_10) / peak_10
        mdd_10 = min(mdd_10, dd)

    print(f"\n[BÁO CÁO TÀI CHÍNH - SOL SUPERTREND (17, 4.3)]")
    print(f"Risk: 10% Tài Khoản Cho 1 Lệnh (Đánh kiểu Lấy số má)")
    print(f"- Vốn ban đầu: 10,000,000 VNĐ")
    print(f"- Vốn cuối kỳ (Sau 4 năm): {cap_10:,.0f} VNĐ")
    print(f"- Hệ số nhân tài khoản: x{cap_10 / 10_000_000:,.1f} lần")
    print(f"- Sụt giảm tối đa (Max Drawdown): {mdd_10*100:.1f}%")
    print(f"- Chuỗi thua dài nhất liên tiếp: {max_loss_streak} lệnh")

run()
