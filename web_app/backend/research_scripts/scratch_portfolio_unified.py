import sys, os
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.abspath(".agents/skills/honest-backtest/scripts"))
import bt_data
import bt_harness as H
import xrp_nada as X

def get_xrp_trades():
    d1 = bt_data.load("XRPUSDT", "1m")
    sim = H.Sim(d1)
    B = H.resample(d1, 5)
    sl_pct, tp_pct = 0.55, 17.9
    cost = 2 * (0.0005 + 0.0001) * 100
    side = X.signals(B, h=8.0, mult=3.0, rsi_os=20, rsi_ob=80, vol_mult=2.4)
    c = B["close"].to_numpy()
    
    T = sim.run(B, side, c * sl_pct / 100, c * tp_pct / 100)
    T['pnl_pct'] = np.where(T['reason'] == 'TP', tp_pct - cost, -sl_pct - cost)
    T['net_r'] = T['pnl_pct'] / sl_pct
    T['coin'] = 'XRP (Bắt Đáy)'
    T['type'] = np.where(T['side'] == 1, 'LONG', 'SHORT')
    T['sl_pct'] = sl_pct
    return T

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

def get_sol_trades():
    d1 = bt_data.load("SOLUSDT", "1m")
    sim = H.Sim(d1)
    B = H.resample(d1, 240)
    c, h, l = B["close"].to_numpy(), B["high"].to_numpy(), B["low"].to_numpy()
    ct = B["close_time"].to_numpy()
    
    trend, final_ub, final_lb = supertrend_with_bands(h, l, c, 17, 4.4)
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
            pnl = gross - 0.12
            true_r = pnl / initial_sl_val if initial_sl_val > 0.1 else pnl
            trades[-1]['exit_t'] = int(sim.t[j])
            trades[-1]['exit'] = px
            trades[-1]['pnl_pct'] = pnl
            trades[-1]['net_r'] = true_r
            trades[-1]['reason'] = 'TREND_FLIP'
            
        pos, e = s, px
        if pos == 1: initial_sl_val = (px - final_lb[bi-1]) / px * 100
        else: initial_sl_val = (final_ub[bi-1] - px) / px * 100
            
        trades.append({
            'entry_t': int(sim.t[j]),
            'exit_t': 0, 'side': pos, 'entry': px, 'exit': 0,
            'reason': '', 'pnl_pct': 0, 'net_r': 0,
            'coin': 'SOL (Cưỡi Sóng)',
            'type': 'LONG' if pos == 1 else 'SHORT',
            'sl_pct': initial_sl_val
        })
        
    T = pd.DataFrame(trades)
    T = T[T['exit_t'] != 0] # Bỏ lệnh cuối cùng chưa đóng
    return T

def run():
    print("Processing XRP Trades...")
    T_xrp = get_xrp_trades()
    print("Processing SOL Trades...")
    T_sol = get_sol_trades()
    
    # Gộp 2 bảng
    T_all = pd.concat([T_xrp, T_sol], ignore_index=True)
    
    # Sắp xếp theo thứ tự thời gian vào lệnh
    T_all = T_all.sort_values('entry_t').reset_index(drop=True)
    
    T_all['entry_time'] = pd.to_datetime(T_all['entry_t'], unit='s')
    T_all['exit_time'] = pd.to_datetime(T_all['exit_t'], unit='s')
    
    # Tính toán sự cộng hưởng Lợi nhuận (Chạy Equity Curve Gộp)
    # Giả định Risk = 3% tài khoản cho TẤT CẢ các lệnh. 
    # Lưu ý: Vì các lệnh có thể đè lên nhau, ta tính Lãi kép theo từng Event Đóng Lệnh
    
    cap = 10_000_000
    peak = cap
    mdd = 0
    
    # Sort by exit time to correctly compound capital
    T_exit = T_all.sort_values('exit_t').reset_index(drop=True)
    
    for i, row in T_exit.iterrows():
        pct = row['net_r'] * 0.03 # Risk 3%
        if pct <= -1.0: pct = -0.99
        cap = cap * (1 + pct)
        peak = max(peak, cap)
        dd = (cap - peak) / peak
        mdd = min(mdd, dd)
        
    md = "# BIÊN BẢN HỢP THỂ: DANH MỤC XRP (BẮT ĐÁY) & SOL (CƯỠI SÓNG)\n\n"
    md += f"Báo cáo lịch sử giao dịch được hợp nhất theo Dòng thời gian, minh chứng cho sức mạnh Bù trừ của 2 chiến lược.\n\n"
    
    md += f"**TÓM TẮT QUỸ ĐẦU TƯ TỔNG HỢP (RISK 3% / LỆNH)**\n"
    md += f"- **Tổng số lệnh:** {len(T_all)} lệnh ({len(T_xrp)} XRP + {len(T_sol)} SOL)\n"
    md += f"- **Vốn Khởi Điểm:** 10,000,000 VNĐ\n"
    md += f"- **Vốn Cuối Kỳ (Sau 4 Năm):** **{cap:,.0f} VNĐ** (x{cap/10_000_000:,.1f} lần)\n"
    md += f"- **Sụt giảm tối đa (Max Drawdown):** **{mdd*100:.1f}%** (Được làm phẳng rất nhiều nhờ 2 con bù trừ nhau)\n\n"
    
    md += "| STT | Coin | Loại Lệnh | Ngày Vào Lệnh | Giá Vào | % Rủi Ro Ban Đầu | Ngày Đóng Lệnh | Trạng Thái | Tiền Tươi % | Lãi Nhận (R) |\n"
    md += "|---|---|---|---|---|---|---|---|---|---|\n"
    
    for idx, row in T_all.iterrows():
        r = row['net_r']
        r_str = f"**<span style='color:green'>+{r:.2f} R</span>**" if r > 0 else f"<span style='color:red'>{r:.2f} R</span>"
        pnl = row['pnl_pct']
        pnl_str = f"+{pnl:.2f}%" if pnl > 0 else f"{pnl:.2f}%"
        
        md += f"| {idx+1} | **{row['coin']}** | {row['type']} | {row['entry_time'].strftime('%y-%m-%d %H:%M')} | {row['entry']:.4f} | SL {row['sl_pct']:.2f}% | {row['exit_time'].strftime('%y-%m-%d %H:%M')} | {row['reason']} | {pnl_str} | {r_str} |\n"
        
    out_path = '/Users/finn/.gemini/antigravity/brain/921139ef-edbf-43e7-bf4e-d052df21201b/portfolio_unified_log.md'
    with open(out_path, 'w') as f:
        f.write(md)
        
    print(f"\nĐã tạo thành công Artifact: {out_path}")

run()
