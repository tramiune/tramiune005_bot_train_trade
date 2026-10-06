import sys, os
import pandas as pd
import numpy as np
import time

sys.path.insert(0, os.path.abspath(".agents/skills/honest-backtest/scripts"))
import bt_data
import bt_harness as H

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
    print("Loading SOLUSDT 1m data...")
    d1 = bt_data.load("SOLUSDT", "1m")
    sim = H.Sim(d1)
    
    # Cấu hình Khung 4H
    B = H.resample(d1, 240)
    c = B["close"].to_numpy()
    h = B["high"].to_numpy()
    l = B["low"].to_numpy()
    ct = B["close_time"].to_numpy()
    
    cost = 0.12 # 0.12% round trip
    rows = []
    
    lengths = list(range(5, 31)) # 5 to 30
    mults = list(np.arange(3.0, 16.0, 0.5)) # 3.0, 3.5 ... 15.5
    
    total_runs = len(lengths) * len(mults)
    print(f"Bắt đầu Quét Đa Chiều (ULTRA GRID) với {total_runs} kịch bản...")
    start_t = time.time()
    
    for length in lengths:
        for mult in mults:
            trend = supertrend(h, l, c, length, mult)
            side = np.zeros(len(B), dtype=int)
            for i in range(1, len(trend)):
                if trend[i] == 1 and trend[i-1] == -1: side[i] = 1
                elif trend[i] == -1 and trend[i-1] == 1: side[i] = -1
                    
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
                
            if len(trades) < 5: continue # Bỏ qua nếu quá ít lệnh
            
            T = pd.DataFrame(trades)
            T['pnl'] = T['gross'] - cost
            
            wins = len(T[T['pnl'] > 0])
            losses = len(T[T['pnl'] <= 0])
            wr = wins / len(T) * 100
            total_pnl = T['pnl'].sum()
            
            avg_loss = abs(T[T['pnl'] < 0]['pnl'].mean())
            if avg_loss == 0 or pd.isna(avg_loss): avg_loss = 5.0
            
            T['r_val'] = T['pnl'] / avg_loss
            net_r = T['r_val'].sum()
            
            rows.append({
                'Khung': '4H', 'Length': length, 'Mult': mult,
                'Số Lệnh': len(T), 'WinRate': wr, 'Lỗ TB': avg_loss,
                'Tổng Lãi %': total_pnl, 'Net_R': net_r
            })

    end_t = time.time()
    print(f"Quét xong {total_runs} cấu hình trong {end_t - start_t:.1f} giây.\n")
    
    df = pd.DataFrame(rows)
    df = df.sort_values('Tổng Lãi %', ascending=False)
    
    print("=== TOP 15 CẤU HÌNH SOL SUPERTREND (LÃI CAO NHẤT) ===")
    print(df.head(15).round(2).to_string(index=False))
    
    out_path = '/Users/finn/.gemini/antigravity/brain/921139ef-edbf-43e7-bf4e-d052df21201b/sol_supertrend_ultra_grid.md'
    md = "# SIÊU QUÉT SUPERTREND CHO SOL (ĐỘ PHÂN GIẢI CAO)\n\n"
    md += f"Đã quét {total_runs} kịch bản với Length từ 5->30 và Multiplier từ 3.0->15.5.\n\n"
    md += "| Khung | Chiều dài | Hệ số (Mult) | Số lệnh | Win Rate | Lỗ Trung Bình | Lãi Ròng (Tiền Tươi) | Lãi Ròng (R) |\n"
    md += "|---|---|---|---|---|---|---|---|\n"
    for i, (_, row) in enumerate(df.head(20).iterrows()):
        md += f"| {row['Khung']} | {row['Length']} | {row['Mult']} | {int(row['Số Lệnh'])} | {row['WinRate']:.1f}% | -{row['Lỗ TB']:.2f}% | **+{row['Tổng Lãi %']:.1f}%** | +{row['Net_R']:.1f} R |\n"
    
    with open(out_path, 'w') as f:
        f.write(md)
    print(f"\nĐã xuất Artifact: {out_path}")

run()
