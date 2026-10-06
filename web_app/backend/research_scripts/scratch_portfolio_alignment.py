import sys, os
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.abspath(".agents/skills/honest-backtest/scripts"))
import bt_data
import bt_harness as H
import xrp_nada as X

def supertrend(h, l, c, period=14, mult=5.0):
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
        if basic_ub[i] < final_ub[i-1] or c[i-1] > final_ub[i-1]:
            final_ub[i] = basic_ub[i]
        else:
            final_ub[i] = final_ub[i-1]
            
        if basic_lb[i] > final_lb[i-1] or c[i-1] < final_lb[i-1]:
            final_lb[i] = basic_lb[i]
        else:
            final_lb[i] = final_lb[i-1]
            
        if trend[i-1] == 1 and c[i] < final_lb[i]:
            trend[i] = -1
        elif trend[i-1] == -1 and c[i] > final_ub[i]:
            trend[i] = 1
        else:
            trend[i] = trend[i-1]
    return trend

def run():
    print("1. Chạy XRP (Bắt đáy Râu Nến)...")
    xrp = bt_data.load("XRPUSDT", "1m")
    sim_xrp = H.Sim(xrp)
    B_xrp = H.resample(xrp, 5)
    
    c_xrp = B_xrp["close"].to_numpy()
    side_xrp = X.signals(B_xrp, h=8.0, mult=3.0, rsi_os=20, rsi_ob=80, vol_mult=2.5)
    T_xrp = sim_xrp.run(B_xrp, side_xrp, c_xrp * 0.55 / 100, c_xrp * 16.5 / 100)
    T_xrp['time'] = pd.to_datetime(T_xrp.exit_t, unit='s')
    cost = 0.24 # 0.12% x 2
    T_xrp['R'] = np.where(T_xrp['reason'] == 'TP', (16.5 - cost)/0.55, (-0.55 - cost)/0.55)
    
    print("2. Chạy SOL (Thuận Xu Hướng 4H)...")
    sol = bt_data.load("SOLUSDT", "1m")
    sim_sol = H.Sim(sol)
    B_sol = H.resample(sol, 240) # 4H
    c = B_sol["close"].to_numpy()
    h = B_sol["high"].to_numpy()
    l = B_sol["low"].to_numpy()
    
    trend = supertrend(h, l, c, 14, 5.0)
    side_sol = np.zeros(len(B_sol), dtype=int)
    for i in range(1, len(trend)):
        if trend[i] == 1 and trend[i-1] == -1: side_sol[i] = 1
        elif trend[i] == -1 and trend[i-1] == 1: side_sol[i] = -1
            
    ct = B_sol["close_time"].to_numpy()
    idx = np.nonzero(side_sol)[0]
    trades, pos, e = [], 0, 0.0
    for bi in idx:
        s = int(side_sol[bi])
        j = np.searchsorted(sim_sol.t, ct[bi])
        if j >= sim_sol.n or sim_sol.t[j] != ct[bi]: continue
        px = sim_sol.o[j]
        if pos != 0:
            gross = pos * (px / e - 1) * 100
            trades.append({'exit_t': int(sim_sol.t[j]), 'gross': gross})
        pos, e = s, px
        
    T_sol = pd.DataFrame(trades)
    T_sol['time'] = pd.to_datetime(T_sol['exit_t'], unit='s')
    T_sol['pnl'] = T_sol['gross'] - cost
    
    avg_sol_loss = abs(T_sol[T_sol['pnl'] < 0]['pnl'].mean())
    if avg_sol_loss == 0 or pd.isna(avg_sol_loss): avg_sol_loss = 7.63
    T_sol['R'] = T_sol['pnl'] / avg_sol_loss
    
    # 3. Gộp Danh Mục Từng Tháng
    xrp_monthly = T_xrp.groupby(T_xrp['time'].dt.strftime('%Y-%m'))['R'].sum().reset_index()
    xrp_monthly.columns = ['Tháng', 'XRP_R']
    
    sol_monthly = T_sol.groupby(T_sol['time'].dt.strftime('%Y-%m'))['R'].sum().reset_index()
    sol_monthly.columns = ['Tháng', 'SOL_R']
    
    merged = pd.merge(xrp_monthly, sol_monthly, on='Tháng', how='outer').fillna(0)
    merged['Danh_Mục_R'] = merged['XRP_R'] + merged['SOL_R']
    
    xrp_loss_months = merged[merged['XRP_R'] < 0]
    saved_months = xrp_loss_months[xrp_loss_months['Danh_Mục_R'] > 0]
    
    print(f"\n=== HIỆU QUẢ HEDGING (BÙ ĐẮP) TỔNG QUAN ===")
    print(f"- Tổng số tháng XRP bị THUA (Âm tiền): {len(xrp_loss_months)} tháng")
    print(f"- Trong đó, SOL đã CỨU (Kéo lại thành Lãi): {len(saved_months)} tháng!")
    
    # Số tháng Danh Mục bị âm tổng (sau khi ghép)
    total_loss_months = merged[merged['Danh_Mục_R'] < 0]
    print(f"- Nếu chỉ đánh XRP, Sếp phải chịu {len(xrp_loss_months)} tháng thua lỗ.")
    print(f"- Nếu ghép cả 2 con, Sếp chỉ còn phải chịu {len(total_loss_months)} tháng thua lỗ! (Bình ổn tâm lý cực cao).")
    
    print("\n=== TOP 5 THÁNG XUẤT SẮC NHẤT (SOL Gánh Team Khi XRP Chết) ===")
    top_saves = saved_months.sort_values('SOL_R', ascending=False).head(5)
    for _, row in top_saves.iterrows():
        print(f"[{row['Tháng']}] XRP Bắt đáy hụt: {row['XRP_R']:.2f} R | SOL Ăn Sóng Dài: +{row['SOL_R']:.2f} R => TỔNG: +{row['Danh_Mục_R']:.2f} R")
        
    print("\n=== TOP 5 THÁNG HOÀN HẢO (Cả 2 Con Cùng Ăn Đậm) ===")
    double_win = merged[(merged['XRP_R'] > 0) & (merged['SOL_R'] > 0)].sort_values('Danh_Mục_R', ascending=False).head(5)
    for _, row in double_win.iterrows():
        print(f"[{row['Tháng']}] XRP Lãi: +{row['XRP_R']:.2f} R | SOL Lãi: +{row['SOL_R']:.2f} R => TỔNG: +{row['Danh_Mục_R']:.2f} R")

run()
