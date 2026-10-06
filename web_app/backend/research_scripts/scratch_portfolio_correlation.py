import sys, os
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.abspath(".agents/skills/honest-backtest/scripts"))
import bt_data
import bt_harness as H
import xrp_nada as X

def run():
    print("1. Loading XRPUSDT (Bắt Đáy / Mean Reversion) ...")
    xrp = bt_data.load("XRPUSDT", "1m")
    sim_xrp = H.Sim(xrp)
    B_xrp = H.resample(xrp, 5)
    c_xrp = B_xrp["close"].to_numpy()
    
    sl_pct = 0.55
    tp_pct = 16.5
    cost = 2 * (0.0005 + 0.0001) * 100
    
    side_xrp = X.signals(B_xrp, h=8.0, mult=3.0, rsi_os=20, rsi_ob=80, vol_mult=2.5)
    T_xrp = sim_xrp.run(B_xrp, side_xrp, c_xrp * sl_pct / 100, c_xrp * tp_pct / 100)
    T_xrp['time'] = pd.to_datetime(T_xrp.exit_t, unit='s')
    T_xrp['pnl_R'] = np.where(T_xrp['reason'] == 'TP', (tp_pct - cost)/sl_pct, (-sl_pct - cost)/sl_pct)
    xrp_monthly = T_xrp.groupby(T_xrp['time'].dt.strftime('%Y-%m'))['pnl_R'].sum().reset_index()
    xrp_monthly.columns = ['month', 'XRP_R']
    
    print("2. Loading DOGEUSDT (Thuận Xu Hướng / Trend Following) ...")
    doge = bt_data.load("DOGEUSDT", "1m")
    sim_doge = H.Sim(doge)
    B_doge = H.resample(doge, 240) # 4H
    
    # Donchian Breakout (20 periods 4H = 80 hours)
    c_d = B_doge["close"].to_numpy()
    h_d = B_doge["high"].to_numpy()
    l_d = B_doge["low"].to_numpy()
    
    upper = pd.Series(h_d).rolling(20).max().shift(1).to_numpy()
    lower = pd.Series(l_d).rolling(20).min().shift(1).to_numpy()
    
    side_doge = np.zeros(len(B_doge))
    pos = 0
    for i in range(20, len(c_d)):
        if c_d[i] > upper[i]:
            pos = 1
        elif c_d[i] < lower[i]:
            pos = -1
        side_doge[i] = pos
        
    # We use original_reversal logic for trend following (Hold until trend flips)
    ct = B_doge["close_time"].to_numpy()
    # Filter to only log when pos changes
    changes = np.where(side_doge[1:] != side_doge[:-1])[0] + 1
    
    trades = []
    e = 0
    p = 0
    for bi in changes:
        s = int(side_doge[bi])
        j = np.searchsorted(sim_doge.t, ct[bi])
        if j >= sim_doge.n or sim_doge.t[j] != ct[bi]: continue
        px = sim_doge.o[j]
        
        if p != 0:
            gross = p * (px / e - 1) * 100
            trades.append({'exit_t': int(sim_doge.t[j]), 'gross': gross})
        
        p = s
        e = px
        
    T_doge = pd.DataFrame(trades)
    if len(T_doge) > 0:
        T_doge['time'] = pd.to_datetime(T_doge['exit_t'], unit='s')
        # Normalize to R: Giả sử cắt lỗ cơ sở là 10% cho 4H, vậy R = gross / 10.0
        T_doge['pnl_R'] = (T_doge['gross'] - cost) / 10.0
        doge_monthly = T_doge.groupby(T_doge['time'].dt.strftime('%Y-%m'))['pnl_R'].sum().reset_index()
        doge_monthly.columns = ['month', 'DOGE_R']
    else:
        doge_monthly = pd.DataFrame(columns=['month', 'DOGE_R'])
    
    print("3. Phân tích Tương quan (Correlation) & Bù đắp (Hedging) ...")
    merged = pd.merge(xrp_monthly, doge_monthly, on='month', how='outer').fillna(0)
    merged['Total_R'] = merged['XRP_R'] + merged['DOGE_R']
    
    xrp_loss_months = merged[merged['XRP_R'] < 0].copy()
    xrp_loss_months['Hedged'] = xrp_loss_months['Total_R'] > 0
    
    saved = xrp_loss_months['Hedged'].sum()
    print(f"\n[PHÂN TÍCH HEDGING DANH MỤC THÁNG]")
    print(f"Tổng số tháng XRP đánh Bắt Đáy bị Lỗ: {len(xrp_loss_months)} tháng")
    print(f"Số tháng DOGE đánh Thuận Xu Hướng đã CỨU (Kéo lại thành Lãi dương): {saved} tháng")
    
    print("\nChi tiết 5 tháng tồi tệ nhất của XRP (Và cách DOGE đã gánh team):")
    worst = xrp_loss_months.sort_values('XRP_R').head(5)
    for _, row in worst.iterrows():
        status = "✅ ĐÃ CỨU" if row['Hedged'] else "❌ THUA CHUNG"
        print(f"Tháng {row['month']}: XRP thua {row['XRP_R']:.2f} R | DOGE mang về {row['DOGE_R']:+.2f} R | Tổng: {row['Total_R']:+.2f} R ({status})")
        
    print(f"\nTổng lợi nhuận 4 năm của XRP: {merged['XRP_R'].sum():+.2f} R")
    print(f"Tổng lợi nhuận 4 năm của DOGE: {merged['DOGE_R'].sum():+.2f} R")
    print(f"TỔNG DANH MỤC: {merged['Total_R'].sum():+.2f} R")

run()
