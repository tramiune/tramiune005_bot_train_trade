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
    
    sl_pct = 0.55
    tp_pct = 17.9
    cost = 2 * (0.0005 + 0.0001) * 100
    
    # Tính toán trước các chỉ báo nặng
    c = B["close"].to_numpy()
    v = B["volume"].to_numpy()
    
    h = 8.0
    mult = 3.0
    w = np.exp(-(np.arange(500) ** 2) / (h * h * 2))
    out = np.convolve(c, w)[: len(c)] / w.sum()
    out[:499] = np.nan
    mae = pd.Series(np.abs(c - out)).rolling(499).mean().to_numpy() * mult
    upper, lower = out + mae, out - mae
    
    # Caching RSI
    r = X.pine_rsi(c, 14)
    vol_ma20 = pd.Series(v).rolling(20).mean().to_numpy()
    
    prev_c, prev_l, prev_u = np.roll(c, 1), np.roll(lower, 1), np.roll(upper, 1)
    cross_dn = (c < lower) & (prev_c >= prev_l)
    cross_up = (c > upper) & (prev_c <= prev_u)
    
    rsi_list = list(range(10, 31)) # 10 to 30
    vol_list = [round(x, 1) for x in np.arange(1.5, 3.6, 0.1)] # 1.5 to 3.5
    
    results = []
    
    print(f"Bắt đầu Siêu Vi Chỉnh RSI (10-30) và Volume (1.5x - 3.5x)...")
    start_t = time.time()
    
    for rsi_os in rsi_list:
        rsi_ob = 100 - rsi_os
        for vol_mult in vol_list:
            high_vol = v > vol_ma20 * vol_mult
            
            buy = cross_dn & (r < rsi_os) & ~high_vol
            sell = cross_up & (r > rsi_ob) & ~high_vol
            side = np.where(buy, 1, np.where(sell, -1, 0))
            side[:1000] = 0
            
            if not np.any(side): continue
            
            T = sim.run(B, side, c * sl_pct / 100, c * tp_pct / 100)
            if len(T) < 5: continue
            
            T['pnl_pct'] = np.where(T['reason'] == 'TP', tp_pct - cost, -sl_pct - cost)
            T['r_val'] = T['pnl_pct'] / sl_pct
            
            trades = len(T)
            wins = len(T[T['reason'] == 'TP'])
            wr = (wins / trades) * 100 if trades > 0 else 0
            net_r = T['r_val'].sum()
            total_pnl = T['pnl_pct'].sum()
            
            results.append({
                'RSI': rsi_os,
                'Vol': vol_mult,
                'Số Lệnh': trades,
                'Win Rate': wr,
                'Tổng Lãi R': net_r
            })
            
    end_t = time.time()
    print(f"Hoàn thành trong {end_t - start_t:.2f}s.\n")
    
    df = pd.DataFrame(results)
    df = df.sort_values('Tổng Lãi R', ascending=False)
    
    print("=== BẢNG XẾP HẠNG SIÊU VI CHỈNH BỘ LỌC CHO XRP ===")
    print(df.head(15).round(2).to_string(index=False))
    
    out_path = '/Users/finn/.gemini/antigravity/brain/921139ef-edbf-43e7-bf4e-d052df21201b/xrp_micro_filters_grid.md'
    md = "# LÕI HẠT NHÂN: SIÊU VI CHỈNH BỘ LỌC RSI & VOLUME\n\n"
    md += f"Cố định Cắt Lỗ 0.55% và Chốt Lời 17.9%. Băm nhỏ RSI từng 1 Giá trị và Volume từng 0.1x.\n\n"
    md += "| Vùng Quá Bán (RSI) | Bùng Nổ Volume | Số lệnh | Win Rate | TỔNG LÃI (R) |\n"
    md += "|---|---|---|---|---|\n"
    for i, (_, row) in enumerate(df.head(20).iterrows()):
        md += f"| **< {row['RSI']}** | **> {row['Vol']:.1f}x** | {int(row['Số Lệnh'])} | {row['Win Rate']:.1f}% | **+{row['Tổng Lãi R']:.1f} R** |\n"
        
    with open(out_path, 'w') as f:
        f.write(md)
        
run()
