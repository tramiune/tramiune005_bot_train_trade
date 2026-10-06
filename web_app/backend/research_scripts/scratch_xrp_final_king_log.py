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
    
    # Cấu hình Final King (+283 R)
    r_os, v_mult, m = 20, 2.5, 3.0
    sl_pct = 0.55
    tp_pct = 16.5
    
    side = X.signals(B, h=8.0, mult=m, rsi_os=r_os, rsi_ob=100-r_os, vol_mult=v_mult)
    c = B["close"].to_numpy()
    
    print(f"Running simulation with SL {sl_pct}% and TP {tp_pct}% ...")
    T = sim.run(B, side, c * sl_pct / 100, c * tp_pct / 100)
    
    T['entry_time'] = pd.to_datetime(T.entry_t, unit='s')
    T['exit_time'] = pd.to_datetime(T.exit_t, unit='s')
    
    cost = 2 * (0.0005 + 0.0001) * 100 # 0.12%
    
    T['pnl_pct'] = np.where(T['reason'] == 'TP', tp_pct - cost, -sl_pct - cost)
    T['is_win'] = T['reason'] == 'TP'
    
    # Generate Markdown Table
    md_content = f"# SAO KÊ CHI TIẾT TỪNG LỆNH: XRP FINAL KING (+283 R)\n\n"
    md_content += f"**Cấu hình Bộ Lọc (Entry):** RSI < {r_os} | Khối lượng > {v_mult}x | Dải lệch {m} STD\n"
    md_content += f"**Cấu hình Quản Trị (Exit):** Cắt Lỗ {sl_pct}% | Chốt Lời {tp_pct}% (Tỷ lệ RR 1 Ăn 30)\n\n"
    
    wins = len(T[T['is_win']])
    losses = len(T[~T['is_win']])
    wr = wins / len(T) * 100
    net_r = T['pnl_pct'].sum() / sl_pct
    
    md_content += f"- **Tổng số lệnh (4 năm):** {len(T)}\n"
    md_content += f"- **Lệnh Thắng:** {wins} ({wr:.2f}%)\n"
    md_content += f"- **Lệnh Thua:** {losses}\n"
    md_content += f"- **Tổng Lãi Ròng (Risk):** +{net_r:.2f} R\n\n"
    
    md_content += "| STT | Thời gian Vào Lệnh | Giá Mua | Thời gian Thoát Lệnh | Trạng thái | Lãi/Lỗ (%) | Lãi/Lỗ (R) |\n"
    md_content += "|---|---|---|---|---|---|---|\n"
    
    for idx, row in T.iterrows():
        pnl = row['pnl_pct']
        r_val = pnl / sl_pct
        status = "WIN 🏆" if row['is_win'] else "LOSS 🩸"
        pnl_str = f"**<span style='color:green'>+{pnl:.2f}%</span>**" if pnl > 0 else f"<span style='color:red'>{pnl:.2f}%</span>"
        r_str = f"**<span style='color:green'>+{r_val:.2f} R</span>**" if r_val > 0 else f"<span style='color:red'>{r_val:.2f} R</span>"
        
        md_content += f"| {idx+1} | {row['entry_time'].strftime('%Y-%m-%d %H:%M')} | {row['entry']:.4f} | {row['exit_time'].strftime('%Y-%m-%d %H:%M')} | {status} | {pnl_str} | {r_str} |\n"
        
    out_path = '/Users/finn/.gemini/antigravity/brain/921139ef-edbf-43e7-bf4e-d052df21201b/xrp_final_king_log.md'
    with open(out_path, 'w') as f:
        f.write(md_content)
        
    print(f"Đã tạo Artifact: {out_path}")

run()
