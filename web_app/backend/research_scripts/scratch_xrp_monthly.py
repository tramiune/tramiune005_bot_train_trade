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
    
    print("Resampling to 5m & Extracting Signals...")
    B = H.resample(d1, 5)
    
    # Extract Nada-Watson signals
    side = X.signals(B)
    c = B["close"].to_numpy()
    
    # RR 10 config (SL 1%, TP 10%)
    sl_pct = 1.0
    tp_pct = 5.0
    
    print(f"Running simulation with SL {sl_pct}% and TP {tp_pct}% ...")
    T = sim.run(B, side, c * sl_pct / 100, c * tp_pct / 100)
    
    # Process trades
    T['exit_time'] = pd.to_datetime(T.exit_t, unit='s')
    T['year'] = T['exit_time'].dt.year
    T['month'] = T['exit_time'].dt.month
    
    # Win condition: reason == "TP"
    T['is_win'] = T['reason'] == 'TP'
    # Calculate R: Win = 5.0R, Loss = -1R
    T['R'] = np.where(T['is_win'], 5.0, -1.0)
    
    print("\n=== ĐÁNH BẮT ĐÁY XRP (RR 1:10) ===")
    print("Vào lệnh: Khi giá bị nén mạnh, báo quá bán (RSI) và lệch dải Nadaraya-Watson")
    print(f"SL: {sl_pct}% | TP: {tp_pct}% (1 ăn 5)")
    
    wr = T['is_win'].mean() * 100
    print(f"\nTổng số lệnh (4 năm): {len(T)}")
    print(f"Lệnh Thắng: {T['is_win'].sum()} | Lệnh Thua: {(~T['is_win']).sum()}")
    print(f"Win Rate THỰC TẾ: {wr:.2f}% (Mốc hòa vốn: ~10.4%)")
    print(f"Tổng Lãi Ròng (Risk): +{T.R.sum():.2f}R\n")
    
    monthly = T.groupby(['year', 'month']).agg(
        trades=('R', 'count'),
        wins=('is_win', 'sum'),
        r_sum=('R', 'sum')
    ).reset_index()
    
    print("=== SAO KÊ CHI TIẾT TỪNG THÁNG ===")
    print("Năm-Tháng | Lệnh | Thắng | Win Rate | Lãi Ròng (Risk)")
    print("-" * 55)
    
    for _, row in monthly.iterrows():
        wr_m = (row['wins'] / row['trades']) * 100 if row['trades'] > 0 else 0
        print(f"{int(row['year'])}-{int(row['month']):02d}    | {int(row['trades']):4d} | {int(row['wins']):4d}  |   {wr_m:5.1f}% | {row['r_sum']:+8.2f} R")

run()
