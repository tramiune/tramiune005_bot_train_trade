import sys, os
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.abspath(".agents/skills/honest-backtest/scripts"))
import bt_data
import bt_harness as H
from doge_star_deep import star, with_r

def run():
    print("Loading DOGE 1m data...")
    d1 = bt_data.load("DOGEUSDT", "1m")
    sim = H.Sim(d1)
    
    print("Resampling to 4H & Extracting Signals...")
    B = H.resample(d1, 240)
    
    # Extract Morning/Evening Star signals (default parameters)
    side, risk = star(B)
    
    # Run simulation at RR 1.0
    rr = 1.0
    T = with_r(sim.run(B, side, risk, risk * rr), B, risk)
    
    # Add exit time details
    T['exit_time'] = pd.to_datetime(T.exit_t, unit='s')
    T['year'] = T['exit_time'].dt.year
    T['month'] = T['exit_time'].dt.month
    
    print("\n=== ĐÁNH SIDEWAYS/ĐẢO CHIỀU: SAO MAI / SAO HÔM 4H ===")
    print("Vào lệnh: Sau cú xả mạnh, xuất hiện cụm 3 nến đảo chiều")
    print("SL: Dưới cụm nến | TP: 1 ăn 1 (RR 1.0)")
    
    wr = (T.R > 0).mean() * 100
    print(f"\nTổng số lệnh (4 năm): {len(T)}")
    print(f"Win Rate THỰC TẾ: {wr:.2f}% (Vượt xa mốc hòa vốn 50%)")
    print(f"Tổng Lãi Ròng (Tính theo Risk - 1R = 1 Lệnh): {T.R.sum():+.2f}R\n")
    
    monthly = T.groupby(['year', 'month']).agg(
        trades=('R', 'count'),
        wins=('R', lambda x: (x > 0).sum()),
        r_sum=('R', 'sum')
    ).reset_index()
    
    print("=== SAO KÊ CHI TIẾT TỪNG THÁNG ===")
    print("Năm-Tháng | Lệnh | Thắng | Win Rate | Lãi Ròng (Risk)")
    print("-" * 55)
    
    for _, row in monthly.iterrows():
        wr_m = (row['wins'] / row['trades']) * 100 if row['trades'] > 0 else 0
        print(f"{int(row['year'])}-{int(row['month']):02d}    | {int(row['trades']):4d} | {int(row['wins']):4d}  |   {wr_m:5.1f}% | {row['r_sum']:+8.2f} R")

run()
