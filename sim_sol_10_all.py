import sys, os, pandas as pd, numpy as np
sys.path.insert(0, os.path.abspath(".agents/skills/honest-backtest/scripts"))
import bt_data, bt_harness as H

sol = bt_data.load("SOLUSDT", "1m")
sim = H.Sim(sol)
B = H.resample(sol, 240) # 4H
c, h, l = B["close"].to_numpy(), B["high"].to_numpy(), B["low"].to_numpy()
ct = B["close_time"].to_numpy()

period, mult = 17, 4.3

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

side = np.zeros(len(B), dtype=int)
for i in range(1, len(trend)):
    if trend[i] == 1 and trend[i-1] == -1: side[i] = 1
    elif trend[i] == -1 and trend[i-1] == 1: side[i] = -1

idx = np.nonzero(side)[0]
trades, pos, e, et = [], 0, 0.0, 0
initial_sl = 0.0

for bi in idx:
    s = int(side[bi])
    j = np.searchsorted(sim.t, ct[bi])
    if j >= sim.n or sim.t[j] != ct[bi]: continue
    px = sim.o[j]
    
    if pos != 0:
        gross = pos * (px / e - 1) * 100
        pnl = gross - 0.12 # fee
        true_r = pnl / initial_sl if initial_sl > 0.5 else pnl / 5.0
        trades.append({
            'entry_t': et,
            'exit_t': int(sim.t[j]),
            'entry_px': e,
            'exit_px': px,
            'type': 'LONG 📈' if pos == 1 else 'SHORT 📉',
            'pnl_pct': pnl,
            'sl_pct': initial_sl,
            'net_r': true_r
        })
    pos, e, et = s, px, int(sim.t[j])
    if pos == 1: initial_sl = (px - final_lb[bi]) / px * 100
    else: initial_sl = (final_ub[bi] - px) / px * 100

T = pd.DataFrame(trades)
T['entry_time'] = pd.to_datetime(T['entry_t'], unit='s')
T['exit_time'] = pd.to_datetime(T['exit_t'], unit='s')

# Simulation 1: Risk 10% on Initial Capital (Fixed fractional risk)
cap_vnd = 15_000_000.0
cap_usd = 580.0
risk_pct = 0.10

peak_vnd = cap_vnd
max_dd = 0.0

rows_md = []

for idx, row in T.iterrows():
    trade_pct = row['net_r'] * risk_pct
    if trade_pct <= -1.0: trade_pct = -0.99
    
    cap_vnd = cap_vnd * (1 + trade_pct)
    cap_usd = cap_usd * (1 + trade_pct)
    peak_vnd = max(peak_vnd, cap_vnd)
    dd = (cap_vnd - peak_vnd) / peak_vnd
    max_dd = min(max_dd, dd)
    
    pnl = row['pnl_pct']
    r_val = row['net_r']
    account_gain = trade_pct * 100
    
    days_held = (row['exit_t'] - row['entry_t']) / (24 * 3600)
    
    if pnl > 0:
        res_str = f"**<span style='color:green'>+{pnl:.2f}% (TK +{account_gain:.1f}%)</span>**"
        r_str = f"**<span style='color:green'>+{r_val:.2f} R</span>**"
    else:
        res_str = f"<span style='color:red'>{pnl:.2f}% (TK {account_gain:.1f}%)</span>"
        r_str = f"<span style='color:red'>{r_val:.2f} R</span>"
        
    dd_str = f"<span style='color:red'>{dd*100:.1f}%</span>" if dd < -0.01 else "0.0%"
    
    entry_str = row['entry_time'].strftime('%y-%m-%d %H:%M')
    exit_str = row['exit_time'].strftime('%y-%m-%d %H:%M')
    
    rows_md.append(
        f"| {idx+1} | {row['type']} | {entry_str} | {row['entry_px']:.2f} | {exit_str} | {row['exit_px']:.2f} | "
        f"{days_held:.1f}d | SL {row['sl_pct']:.1f}% | {res_str} | {r_str} | **{cap_vnd:,.0f} đ** | {dd_str} |"
    )

header = f"""# 📊 BẢNG SAO KÊ CHI TIẾT TỪNG LỆNH: SOL BOT (RISK 10% / LỆNH)

**Chiến lược:** Cưỡi Sóng Dài Hạn (Supertrend 17, 4.3 - Khung 4H)  
**Vốn khởi điểm:** 15.000.000 VNĐ ($580 USDT)  
**Rủi ro mỗi lệnh:** **10.0%** tài khoản (Fixed Fractional Risk)  
**Tổng số lệnh:** {len(T)} lệnh ({(T['type'].str.contains('LONG')).sum()} Long, {(T['type'].str.contains('SHORT')).sum()} Short)  
- **Lệnh Lãi:** {(T['pnl_pct'] > 0).sum()} lệnh ({(T['pnl_pct'] > 0).mean()*100:.2f}%)  
- **Lệnh Lỗ:** {(T['pnl_pct'] <= 0).sum()} lệnh ({(T['pnl_pct'] <= 0).mean()*100:.2f}%)  
- **Vốn kết thúc (Sau 4 năm):** **{cap_vnd:,.0f} VNĐ** (~{cap_vnd/1e9:.1f} Tỷ VNĐ / ${cap_usd:,.0f})  
- **Sụt giảm tài khoản lớn nhất (Max Drawdown):** **{max_dd*100:.2f}%**  

---

| STT | Vị Thế | Ngày Vào | Giá Vào | Ngày Ra | Giá Ra | Giữ | SL Khởi Điểm | Lãi/Lỗ Tiền Tươi (% TK) | Lãi (R) | Số Dư Sau Lệnh (VNĐ) | Sụt Giảm Đỉnh |
|---|---|---|---|---|---|---|---|---|---|---|---|
"""

full_content = header + "\n".join(rows_md)

out_file = "/Users/finn/.gemini/antigravity/brain/921139ef-edbf-43e7-bf4e-d052df21201b/sol_risk_10_log.md"
with open(out_file, "w") as f:
    f.write(full_content)

print(f"Artifact created: {out_file}")
print("=== SOL RISK 10% FULL SUMMARY ===")
print(f"Total Trades: {len(T)}")
print(f"Wins: {(T['pnl_pct'] > 0).sum()} | Losses: {(T['pnl_pct'] <= 0).sum()}")
print(f"Win Rate: {(T['pnl_pct'] > 0).mean()*100:.2f}%")
print(f"Start Capital: 15,000,000 VND ($580)")
print(f"Final Capital: {cap_vnd:,.0f} VND (${cap_usd:,.0f})")
print(f"Max Drawdown: {max_dd*100:.2f}%")
