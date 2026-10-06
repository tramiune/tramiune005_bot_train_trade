import sys, os, pandas as pd, numpy as np
sys.path.insert(0, os.path.abspath(".agents/skills/honest-backtest/scripts"))
import bt_data, bt_harness as H, xrp_nada as X

# 1. LOAD XRP TRADES
d1_xrp = bt_data.load("XRPUSDT", "1m")
sim_xrp = H.Sim(d1_xrp)
B_xrp = H.resample(d1_xrp, 5)
side_xrp = X.signals(B_xrp, h=8.0, mult=3.0, rsi_os=20, rsi_ob=80, vol_mult=2.4)
c_xrp = B_xrp["close"].to_numpy()
sl_pct_xrp, tp_pct_xrp = 0.55, 17.9
cost = 2 * (0.0005 + 0.0001) * 100

T_xrp = sim_xrp.run(B_xrp, side_xrp, c_xrp * sl_pct_xrp / 100, c_xrp * tp_pct_xrp / 100)
H.check_trades(T_xrp)
T_xrp["pnl_pct"] = np.where(T_xrp["reason"] == "TP", tp_pct_xrp - cost, -sl_pct_xrp - cost)
T_xrp["net_r"] = T_xrp["pnl_pct"] / sl_pct_xrp
T_xrp["entry_dt"] = pd.to_datetime(T_xrp["entry_t"], unit="s")
T_xrp["exit_dt"] = pd.to_datetime(T_xrp["exit_t"], unit="s")
T_xrp["coin"] = "XRP (Bắt Đáy)"
T_xrp["type"] = np.where(T_xrp["side"] == 1, "LONG 📈", "SHORT 📉")

# 2. LOAD SOL TRADES
sol = bt_data.load("SOLUSDT", "1m")
sim_sol = H.Sim(sol)
B_sol = H.resample(sol, 240)
c_sol, h_sol, l_sol = B_sol["close"].to_numpy(), B_sol["high"].to_numpy(), B_sol["low"].to_numpy()
ct_sol = B_sol["close_time"].to_numpy()

period, mult = 17, 4.3
tr1 = h_sol - l_sol
tr2 = np.abs(h_sol - np.roll(c_sol, 1))
tr3 = np.abs(l_sol - np.roll(c_sol, 1))
tr = np.maximum(tr1, np.maximum(tr2, tr3))
tr[0] = tr1[0]
atr = np.zeros(len(c_sol))
atr[0] = tr[0]
for i in range(1, len(c_sol)): atr[i] = (atr[i-1] * (period - 1) + tr[i]) / period

hl2 = (h_sol + l_sol) / 2
basic_ub = hl2 + mult * atr
basic_lb = hl2 - mult * atr
final_ub = np.zeros(len(c_sol))
final_lb = np.zeros(len(c_sol))
trend = np.ones(len(c_sol))

for i in range(1, len(c_sol)):
    if basic_ub[i] < final_ub[i-1] or c_sol[i-1] > final_ub[i-1]: final_ub[i] = basic_ub[i]
    else: final_ub[i] = final_ub[i-1]
    if basic_lb[i] > final_lb[i-1] or c_sol[i-1] < final_lb[i-1]: final_lb[i] = basic_lb[i]
    else: final_lb[i] = final_lb[i-1]
    if trend[i-1] == 1 and c_sol[i] < final_lb[i]: trend[i] = -1
    elif trend[i-1] == -1 and c_sol[i] > final_ub[i]: trend[i] = 1
    else: trend[i] = trend[i-1]

side_sol = np.zeros(len(B_sol), dtype=int)
for i in range(1, len(trend)):
    if trend[i] == 1 and trend[i-1] == -1: side_sol[i] = 1
    elif trend[i] == -1 and trend[i-1] == 1: side_sol[i] = -1

idx_sol = np.nonzero(side_sol)[0]
trades_sol, pos, e, et = [], 0, 0.0, 0
initial_sl = 0.0

for bi in idx_sol:
    s = int(side_sol[bi])
    j = np.searchsorted(sim_sol.t, ct_sol[bi])
    if j >= sim_sol.n or sim_sol.t[j] != ct_sol[bi]: continue
    px = sim_sol.o[j]
    if pos != 0:
        gross = pos * (px / e - 1) * 100
        pnl = gross - 0.12
        true_r = pnl / initial_sl if initial_sl > 0.5 else pnl / 5.0
        trades_sol.append({
            'entry_t': et,
            'exit_t': int(sim_sol.t[j]),
            'entry': e,
            'exit': px,
            'type': 'LONG 📈' if pos == 1 else 'SHORT 📉',
            'pnl_pct': pnl,
            'net_r': true_r,
            'coin': 'SOL (Cưỡi Sóng)',
            'reason': 'TREND_FLIP'
        })
    pos, e, et = s, px, int(sim_sol.t[j])
    if pos == 1: initial_sl = (px - final_lb[bi]) / px * 100
    else: initial_sl = (final_ub[bi] - px) / px * 100

T_sol = pd.DataFrame(trades_sol)
T_sol["entry_dt"] = pd.to_datetime(T_sol["entry_t"], unit="s")
T_sol["exit_dt"] = pd.to_datetime(T_sol["exit_t"], unit="s")

# 3. MERGE ALL TRADES CHRONOLOGICALLY BY EXIT TIME
cols = ["coin", "type", "entry_dt", "exit_dt", "entry", "exit", "pnl_pct", "net_r", "reason"]
all_trades = pd.concat([T_xrp[cols], T_sol[cols]], ignore_index=True)
all_trades = all_trades.sort_values("exit_dt").reset_index(drop=True)

# 4. SIMULATION WITH 30M TOTAL (15M XRP + 15M SOL) AT 10% RISK PER ACCOUNT
xrp_bal = 15_000_000.0
sol_bal = 15_000_000.0
total_bal = xrp_bal + sol_bal
peak_total = total_bal
max_portfolio_dd = 0.0

timeline_rows = []

for idx, row in all_trades.iterrows():
    coin = row["coin"]
    net_r = row["net_r"]
    trade_pct = net_r * 0.10 # 10% risk of that coin's account
    if trade_pct <= -1.0: trade_pct = -0.99
    
    if "XRP" in coin:
        pnl_vnd = xrp_bal * trade_pct
        xrp_bal += pnl_vnd
    else:
        pnl_vnd = sol_bal * trade_pct
        sol_bal += pnl_vnd
        
    total_bal = xrp_bal + sol_bal
    peak_total = max(peak_total, total_bal)
    port_dd = (total_bal - peak_total) / peak_total
    max_portfolio_dd = min(max_portfolio_dd, port_dd)
    
    # Format strings
    if row["pnl_pct"] > 0:
        res_str = f"**<span style='color:green'>WIN (+{row['pnl_pct']:.1f}%)</span>**"
        r_str = f"**<span style='color:green'>+{net_r:.2f} R</span>**"
        pnl_vnd_str = f"**<span style='color:green'>+{pnl_vnd:,.0f} đ</span>**"
    else:
        res_str = f"<span style='color:red'>LOSS ({row['pnl_pct']:.1f}%)</span>"
        r_str = f"<span style='color:red'>{net_r:.2f} R</span>"
        pnl_vnd_str = f"<span style='color:red'>{pnl_vnd:,.0f} đ</span>"
        
    dd_str = f"<span style='color:red'>{port_dd*100:.1f}%</span>" if port_dd < -0.01 else "0.0%"
    
    timeline_rows.append(
        f"| {idx+1} | {row['exit_dt'].strftime('%y-%m-%d %H:%M')} | **{coin}** | {row['type']} | "
        f"{row['entry']:.4f} | {row['exit']:.4f} | {res_str} | {r_str} | {pnl_vnd_str} | "
        f"{xrp_bal:,.0f} đ | {sol_bal:,.0f} đ | **{total_bal:,.0f} đ** | {dd_str} |"
    )

header = f"""# 📈 BIÊN BẢN HỢP THỂ LÃI KÉP THEO DÒNG THỜI GIAN (CHRONOLOGICAL TIMELINE)

**Tổng vốn ban đầu:** **30.000.000 VNĐ** (15 triệu Ví XRP + 15 triệu Ví SOL)  
**Quy tắc rủi ro:** **10.0%** trên số dư ví của mỗi con Bot  
**Tổng số giao dịch:** **{len(all_trades)} lệnh** ({len(T_xrp)} XRP + {len(T_sol)} SOL)  
- **Vốn kết thúc (Sau 4 năm):** **{total_bal:,.0f} VNĐ** (~{total_bal/1e9:.1f} TỶ VNĐ / ${total_bal/25800:,.0f})  
  - Ví XRP: **{xrp_bal:,.0f} VNĐ**  
  - Ví SOL: **{sol_bal:,.0f} VNĐ**  
- **Sụt giảm danh mục lớn nhất (Max Portfolio Drawdown):** **{max_portfolio_dd*100:.2f}%**  
*(Nhờ 2 con bù trừ nhau, sụt giảm của cả quỹ giảm mạnh từ -83.8% xuống chỉ còn {max_portfolio_dd*100:.2f}%)*

---

| STT | Thời Điểm Đóng Lệnh | Bot Thực Thi | Loại Lệnh | Giá Vào | Giá Ra | Kết Quả | Lãi (R) | Lãi/Lỗ Lệnh (VNĐ) | Ví XRP | Ví SOL | TỔNG TÀI SẢN (VNĐ) | Sụt Giảm Đỉnh Tổng |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
"""

full_content = header + "\n".join(timeline_rows)
out_file = "/Users/finn/.gemini/antigravity/brain/921139ef-edbf-43e7-bf4e-d052df21201b/portfolio_timeline_10pct_log.md"

with open(out_file, "w") as f:
    f.write(full_content)

print(f"Artifact created: {out_file}")
print("=== TIMELINE MERGED COMPACT SUMMARY ===")
print(f"Total Combined Trades: {len(all_trades)}")
print(f"Start Capital: 30,000,000 VND")
print(f"Final Total Capital: {total_bal:,.0f} VND")
print(f"  - XRP Wallet: {xrp_bal:,.0f} VND")
print(f"  - SOL Wallet: {sol_bal:,.0f} VND")
print(f"Max Portfolio Drawdown: {max_portfolio_dd*100:.2f}%")
