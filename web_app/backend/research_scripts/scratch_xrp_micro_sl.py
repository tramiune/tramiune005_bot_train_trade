import sys, os
import pandas as pd
import numpy as np
import time

sys.path.insert(0, os.path.abspath(".agents/skills/honest-backtest/scripts"))
import bt_data
import bt_harness as H
import xrp_nada as X

def run():
    print("Loading XRPUSDT 1m data...")
    d1 = bt_data.load("XRPUSDT", "1m")
    sim = H.Sim(d1)
    B = H.resample(d1, 5)
    
    tp_pct = 17.9
    sl_list = [round(x, 2) for x in np.arange(0.40, 0.71, 0.01)]
    
    cost = 2 * (0.0005 + 0.0001) * 100
    
    side = X.signals(B, h=8.0, mult=3.0, rsi_os=20, rsi_ob=80, vol_mult=2.5)
    c = B["close"].to_numpy()
    
    results = []
    
    print(f"Bắt đầu Quét SIÊU VI CHỈNH Cắt Lỗ (SL) từ 0.40% đến 0.70% (Bước nhảy 0.01%)...")
    start_t = time.time()
    
    for sl_pct in sl_list:
        T = sim.run(B, side, c * sl_pct / 100, c * tp_pct / 100)
        
        T['pnl_pct'] = np.where(T['reason'] == 'TP', tp_pct - cost, -sl_pct - cost)
        T['r_val'] = T['pnl_pct'] / sl_pct
        
        trades = len(T)
        wins = len(T[T['reason'] == 'TP'])
        wr = (wins / trades) * 100 if trades > 0 else 0
        net_r = T['r_val'].sum()
        total_pnl = T['pnl_pct'].sum()
        
        results.append({
            'SL': sl_pct,
            'TP': tp_pct,
            'Số Lệnh': trades,
            'Win Rate': wr,
            'Tổng Tiền Tươi %': total_pnl,
            'Tổng Lãi R': net_r
        })
        
    end_t = time.time()
    print(f"Hoàn thành trong {end_t - start_t:.2f}s.\n")
    
    df = pd.DataFrame(results)
    df = df.sort_values('Tổng Lãi R', ascending=False)
    
    print("=== BẢNG XẾP HẠNG SIÊU VI CHỈNH CẮT LỖ (SL) CHO XRP ===")
    print(df.head(15).round(2).to_string(index=False))
    
    out_path = '/Users/finn/.gemini/antigravity/brain/921139ef-edbf-43e7-bf4e-d052df21201b/xrp_micro_fine_sl_grid.md'
    md = "# CẤP ĐỘ NGUYÊN TỬ: SIÊU VI CHỈNH CẮT LỖ (SL) XRP\n\n"
    md += f"Cố định TP ở mức Vua 17.9%, dùng kính hiển vi soi SL từng 0.01%.\n\n"
    md += "| Cắt Lỗ (SL) | Chốt Lời (TP) | Số lệnh | Win Rate | Lãi Ròng Tiền Tươi | TỔNG LÃI (R) |\n"
    md += "|---|---|---|---|---|---|\n"
    for i, (_, row) in enumerate(df.head(20).iterrows()):
        md += f"| **{row['SL']:.2f}%** | {row['TP']:.1f}% | {int(row['Số Lệnh'])} | {row['Win Rate']:.1f}% | +{row['Tổng Tiền Tươi %']:.1f}% | **+{row['Tổng Lãi R']:.1f} R** |\n"
        
    with open(out_path, 'w') as f:
        f.write(md)
        
run()
