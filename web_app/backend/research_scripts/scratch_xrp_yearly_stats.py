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
    
    # Cấu hình Vua 1 ăn 30
    sl_pct = 0.55
    tp_pct = 16.5
    cost = 2 * (0.0005 + 0.0001) * 100
    
    side = X.signals(B, h=8.0, mult=3.0, rsi_os=20, rsi_ob=80, vol_mult=2.5)
    c = B["close"].to_numpy()
    
    T = sim.run(B, side, c * sl_pct / 100, c * tp_pct / 100)
    T['entry_time'] = pd.to_datetime(T.entry_t, unit='s')
    T['pnl_pct'] = np.where(T['reason'] == 'TP', tp_pct - cost, -sl_pct - cost)
    T['r_val'] = T['pnl_pct'] / sl_pct
    T['year'] = T['entry_time'].dt.year
    T['month'] = T['entry_time'].dt.month
    
    print("\n[BÁO CÁO TỔNG KẾT THEO TỪNG NĂM]")
    yearly = T.groupby('year').agg(
        trades=('r_val', 'count'),
        wins=('reason', lambda x: (x == 'TP').sum()),
        net_r=('r_val', 'sum')
    )
    
    for year, row in yearly.iterrows():
        wr = (row['wins'] / row['trades']) * 100 if row['trades'] > 0 else 0
        print(f"NĂM {year}: Đánh {row['trades']} lệnh | Thắng {row['wins']} lệnh ({wr:.1f}%) | Lãi Ròng: +{row['net_r']:.2f} R")
        
    print("\n[BÁO CÁO CÁC THÁNG BỊ ÂM]")
    monthly = T.groupby(['year', 'month']).agg(
        trades=('r_val', 'count'),
        wins=('reason', lambda x: (x == 'TP').sum()),
        net_r=('r_val', 'sum')
    ).reset_index()
    
    loss_months = monthly[monthly['net_r'] < 0]
    win_months = monthly[monthly['net_r'] > 0]
    
    print(f"- Tổng số tháng giao dịch: {len(monthly)} tháng (Những tháng không có lệnh không tính).")
    print(f"- Số tháng CÓ LÃI DƯƠNG: {len(win_months)} tháng.")
    print(f"- Số tháng BỊ ÂM (Chuỗi thua rỉ máu): {len(loss_months)} tháng.")
    
    print(f"\nBa tháng thảm họa nhất (Thua lỗ nhiều nhất):")
    worst = loss_months.sort_values('net_r').head(3)
    for _, row in worst.iterrows():
        print(f"Tháng {row['month']}/{row['year']}: Đánh {row['trades']} thua sạch | Âm: {row['net_r']:.2f} R")
        
    print(f"\nBa tháng Bùng Nổ nhất (Siêu lợi nhuận):")
    best = win_months.sort_values('net_r', ascending=False).head(3)
    for _, row in best.iterrows():
        print(f"Tháng {row['month']}/{row['year']}: Đánh {row['trades']} lệnh, thắng {row['wins']} | Lãi: +{row['net_r']:.2f} R")

run()
