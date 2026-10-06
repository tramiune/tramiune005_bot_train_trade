import sys, os
import pandas as pd
import numpy as np

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
    sol = bt_data.load("SOLUSDT", "1m")
    sim = H.Sim(sol)
    B = H.resample(sol, 240) # 4H
    
    c = B["close"].to_numpy()
    h = B["high"].to_numpy()
    l = B["low"].to_numpy()
    
    trend = supertrend(h, l, c, 14, 5.0)
    side = np.zeros(len(B), dtype=int)
    for i in range(1, len(trend)):
        if trend[i] == 1 and trend[i-1] == -1: side[i] = 1
        elif trend[i] == -1 and trend[i-1] == 1: side[i] = -1
            
    ct = B["close_time"].to_numpy()
    idx = np.nonzero(side)[0]
    trades, pos, e, et = [], 0, 0.0, 0
    for bi in idx:
        s = int(side[bi])
        j = np.searchsorted(sim.t, ct[bi])
        if j >= sim.n or sim.t[j] != ct[bi]: continue
        px = sim.o[j]
        if pos != 0:
            gross = pos * (px / e - 1) * 100
            trades.append({
                'entry_t': et,
                'exit_t': int(sim.t[j]), 
                'entry_px': e,
                'exit_px': px,
                'type': 'LONG 📈' if pos == 1 else 'SHORT 📉',
                'gross': gross
            })
        pos, e, et = s, px, int(sim.t[j])
        
    T = pd.DataFrame(trades)
    cost = 0.12 # 0.12% round trip
    T['pnl'] = T['gross'] - cost
    
    T['entry_time'] = pd.to_datetime(T['entry_t'], unit='s')
    T['exit_time'] = pd.to_datetime(T['exit_t'], unit='s')
    
    # Generate Markdown Table
    md = f"# SAO KÊ CHI TIẾT TỪNG LỆNH: SOL SUPERTREND 4H (+644%)\n\n"
    md += f"**Chiến lược:** Thuận Xu Hướng (Gồng Lãi Vô Cực)\n"
    md += f"**Chỉ báo:** Supertrend (Length 14, Multiplier 5.0) trên nến 4 Giờ\n\n"
    
    wins = len(T[T['pnl'] > 0])
    losses = len(T[T['pnl'] <= 0])
    wr = wins / len(T) * 100
    total_pnl = T['pnl'].sum()
    
    md += f"- **Tổng số lệnh (4 năm):** {len(T)}\n"
    md += f"- **Lệnh Thắng:** {wins} ({wr:.2f}%)\n"
    md += f"- **Lệnh Thua:** {losses}\n"
    md += f"- **Tổng Lãi Ròng Tiền Tươi (Chưa đòn bẩy):** +{total_pnl:.2f}%\n\n"
    
    md += "| STT | Loại Lệnh | Thời gian Vào Lệnh | Giá Mua | Thời gian Thoát Lệnh | Giá Thoát | Lãi/Lỗ (%) |\n"
    md += "|---|---|---|---|---|---|---|\n"
    
    for idx, row in T.iterrows():
        pnl = row['pnl']
        pnl_str = f"**<span style='color:green'>+{pnl:.2f}%</span>**" if pnl > 0 else f"<span style='color:red'>{pnl:.2f}%</span>"
        md += f"| {idx+1} | {row['type']} | {row['entry_time'].strftime('%Y-%m-%d %H:%M')} | {row['entry_px']:.2f} | {row['exit_time'].strftime('%Y-%m-%d %H:%M')} | {row['exit_px']:.2f} | {pnl_str} |\n"
        
    out_path = '/Users/finn/.gemini/antigravity/brain/921139ef-edbf-43e7-bf4e-d052df21201b/sol_supertrend_log.md'
    with open(out_path, 'w') as f:
        f.write(md)
        
    print(f"Đã tạo Artifact: {out_path}")

run()
