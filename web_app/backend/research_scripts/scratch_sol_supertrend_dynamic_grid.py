import sys, os
import pandas as pd
import numpy as np
import time

sys.path.insert(0, os.path.abspath(".agents/skills/honest-backtest/scripts"))
import bt_data
import bt_harness as H

def supertrend_with_bands(h, l, c, period, mult):
    tr1 = h - l
    tr2 = np.abs(h - np.roll(c, 1))
    tr3 = np.abs(l - np.roll(c, 1))
    tr = np.maximum(tr1, np.maximum(tr2, tr3))
    tr[0] = tr1[0]
    
    atr = np.zeros(len(c))
    atr[0] = tr[0]
    for i in range(1, len(c)): atr[i] = (atr[i-1] * (period - 1) + tr[i]) / period
        
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
    return trend, final_ub, final_lb

def run():
    print("Loading SOLUSDT 1m data...")
    d1 = bt_data.load("SOLUSDT", "1m")
    sim = H.Sim(d1)
    B = H.resample(d1, 240) # 4H
    c = B["close"].to_numpy()
    h = B["high"].to_numpy()
    l = B["low"].to_numpy()
    ct = B["close_time"].to_numpy()
    
    lengths = list(range(10, 26))
    mults = [round(x, 1) for x in np.arange(3.5, 5.6, 0.1)]
    
    rows = []
    cost = 0.12
    total_runs = len(lengths) * len(mults)
    
    print(f"Bắt đầu Quét Đa Chiều dựa trên True R (Đòn Bẩy Động) với {total_runs} kịch bản...")
    start_t = time.time()
    
    for length in lengths:
        for mult in mults:
            trend, final_ub, final_lb = supertrend_with_bands(h, l, c, length, mult)
            side = np.zeros(len(B), dtype=int)
            for i in range(1, len(trend)):
                if trend[i] == 1 and trend[i-1] == -1: side[i] = 1
                elif trend[i] == -1 and trend[i-1] == 1: side[i] = -1
                    
            idx = np.nonzero(side)[0]
            trades, pos, e = [], 0, 0.0
            initial_sl_val = 0.0
            
            for bi in idx:
                s = int(side[bi])
                j = np.searchsorted(sim.t, ct[bi])
                if j >= sim.n or sim.t[j] != ct[bi]: continue
                px = sim.o[j]
                
                if pos != 0:
                    gross = pos * (px / e - 1) * 100
                    pnl = gross - cost
                    # Bảo vệ chia cho 0
                    if initial_sl_val > 0.1:
                        true_r = pnl / initial_sl_val
                    else:
                        true_r = pnl / 1.0 # fallback
                    trades.append({'pnl': pnl, 'true_r': true_r})
                    
                pos, e = s, px
                
                if pos == 1:
                    sl_price = final_lb[bi-1]
                    initial_sl_val = (px - sl_price) / px * 100
                else:
                    sl_price = final_ub[bi-1]
                    initial_sl_val = (sl_price - px) / px * 100
                    
            if len(trades) < 5: continue
            
            T = pd.DataFrame(trades)
            wins = len(T[T['pnl'] > 0])
            wr = wins / len(T) * 100
            total_pnl = T['pnl'].sum()
            total_true_r = T['true_r'].sum()
            
            rows.append({
                'Khung': '4H', 'Length': length, 'Mult': mult,
                'Số Lệnh': len(T), 'WinRate': wr,
                'Tổng Lãi %': total_pnl, 'True_R': total_true_r
            })

    end_t = time.time()
    print(f"Quét xong trong {end_t - start_t:.1f} giây.\n")
    
    df = pd.DataFrame(rows)
    # Xếp hạng dựa trên TRUE R chứ không phải Tổng Lãi %
    df = df.sort_values('True_R', ascending=False)
    
    print("=== TOP 15 CẤU HÌNH THEO ĐÒN BẨY ĐỘNG (TRUE R) ===")
    print(df.head(15).round(2).to_string(index=False))
    
    out_path = '/Users/finn/.gemini/antigravity/brain/921139ef-edbf-43e7-bf4e-d052df21201b/sol_dynamic_r_grid.md'
    md = "# SIÊU QUÉT DỰA TRÊN ĐÒN BẨY ĐỘNG (TRUE R MAXIMIZATION)\n\n"
    md += f"Đã quét các cấu hình và tính chính xác SL của từng lệnh ngay tại thời điểm vào lệnh để xếp hạng thực tế nhất.\n\n"
    md += "| Khung | Chiều dài | Hệ số (Mult) | Số lệnh | Win Rate | Lãi Ròng (Tiền Tươi) | TỔNG LỢI NHUẬN ĐỘNG (TRUE R) |\n"
    md += "|---|---|---|---|---|---|---|\n"
    for i, (_, row) in enumerate(df.head(20).iterrows()):
        md += f"| {row['Khung']} | {row['Length']} | {row['Mult']} | {int(row['Số Lệnh'])} | {row['WinRate']:.1f}% | +{row['Tổng Lãi %']:.1f}% | **+{row['True_R']:.1f} R** |\n"
    
    with open(out_path, 'w') as f:
        f.write(md)
        
run()
