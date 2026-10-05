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
    
    side = X.signals(B)
    c = B["close"].to_numpy()
    
    # Cấu hình tối ưu (SL 1%, TP 10%)
    sl_pct = 1.0
    tp_pct = 10.0
    
    print(f"Running simulation with SL {sl_pct}% and TP {tp_pct}% ...")
    T = sim.run(B, side, c * sl_pct / 100, c * tp_pct / 100)
    
    T['entry_time'] = pd.to_datetime(T.entry_t, unit='s')
    T['exit_time'] = pd.to_datetime(T.exit_t, unit='s')
    
    # Calculate fees and PnL exactly like honest-backtest
    # FEE_SIDE = 0.0005, SLIP_SIDE = 0.0001
    cost = 2 * (0.0005 + 0.0001) * 100 # In percentage: 0.12%
    
    T['pnl_pct'] = np.where(T['reason'] == 'TP', tp_pct - cost, -sl_pct - cost)
    T['is_win'] = T['reason'] == 'TP'
    
    # Generate Markdown Table
    md_content = f"# BÁO CÁO CHI TIẾT TỪNG LỆNH: XRP 5M BẮT ĐÁY\n\n"
    md_content += f"**Cấu hình Tối Ưu Lợi Nhuận: Cắt Lỗ {sl_pct}% | Chốt Lời {tp_pct}% (RR 1 Ăn 10)**\n\n"
    
    wins = len(T[T['is_win']])
    losses = len(T[~T['is_win']])
    wr = wins / len(T) * 100
    
    md_content += f"- **Tổng số lệnh (4 năm):** {len(T)}\n"
    md_content += f"- **Lệnh Thắng:** {wins} ({wr:.1f}%)\n"
    md_content += f"- **Lệnh Thua:** {losses}\n"
    md_content += f"- **Mốc Hòa Vốn Toán Học:** {100 / (1 + tp_pct/sl_pct):.1f}%\n"
    md_content += f"- **Tổng Lãi Ròng (Risk):** +{T['pnl_pct'].sum() / sl_pct:.2f} R\n\n"
    
    md_content += "| STT | Thời gian Vào Lệnh | Giá Mua | Thời gian Thoát Lệnh | Trạng thái | Lãi/Lỗ (%) | Lãi/Lỗ (R) |\n"
    md_content += "|---|---|---|---|---|---|---|\n"
    
    for idx, row in T.iterrows():
        pnl = row['pnl_pct']
        r_val = pnl / sl_pct
        status = "WIN 🏆" if row['is_win'] else "LOSS 🩸"
        pnl_str = f"**<span style='color:green'>+{pnl:.2f}%</span>**" if pnl > 0 else f"<span style='color:red'>{pnl:.2f}%</span>"
        r_str = f"**<span style='color:green'>+{r_val:.2f} R</span>**" if r_val > 0 else f"<span style='color:red'>{r_val:.2f} R</span>"
        
        md_content += f"| {idx+1} | {row['entry_time'].strftime('%Y-%m-%d %H:%M')} | {row['entry']:.4f} | {row['exit_time'].strftime('%Y-%m-%d %H:%M')} | {status} | {pnl_str} | {r_str} |\n"
        
    out_path = '/Users/finn/.gemini/antigravity/brain/921139ef-edbf-43e7-bf4e-d052df21201b/xrp_trade_log.md'
    with open(out_path, 'w') as f:
        f.write(md_content)
        
    print(f"Đã tạo Artifact: {out_path}")

run()
