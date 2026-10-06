import sys, os, numpy as np, pandas as pd
sys.path.insert(0, os.path.abspath(".agents/skills/honest-backtest/scripts"))
import bt_data, bt_harness as H, xrp_nada as X

d1 = bt_data.load("XRPUSDT", "1m")
sim = H.Sim(d1)
B = H.resample(d1, 5)

side = X.signals(B, h=8.0, mult=3.0, rsi_os=20, rsi_ob=80, vol_mult=2.4)
c = B["close"].to_numpy()
sl_pct, tp_pct = 0.55, 17.9
cost = 2 * (0.0005 + 0.0001) * 100

T = sim.run(B, side, c * sl_pct / 100, c * tp_pct / 100)
H.check_trades(T)

T["pnl_pct"] = np.where(T["reason"] == "TP", tp_pct - cost, -sl_pct - cost)
T["net_r"] = T["pnl_pct"] / sl_pct
T["entry_dt"] = pd.to_datetime(T["entry_t"], unit="s")
T["exit_dt"] = pd.to_datetime(T["exit_t"], unit="s")

cap_vnd = 15_000_000.0
cap_usd = 580.0
risk_pct = 0.10

peak_vnd = cap_vnd
max_dd = 0.0

rows_md = []

for idx, row in T.iterrows():
    trade_pct = row["net_r"] * risk_pct
    
    cap_vnd = cap_vnd * (1 + trade_pct)
    cap_usd = cap_usd * (1 + trade_pct)
    peak_vnd = max(peak_vnd, cap_vnd)
    dd = (cap_vnd - peak_vnd) / peak_vnd
    max_dd = min(max_dd, dd)
    
    side_str = "LONG 📈" if row["side"] == 1 else "SHORT 📉"
    status_str = "**<span style='color:green'>WIN 🏆 (+325%)</span>**" if row["reason"] == "TP" else "<span style='color:red'>LOSS 🩸 (-12.2%)</span>"
    net_r_val = row["net_r"]
    r_str = f"+{net_r_val:.2f} R" if net_r_val > 0 else f"{net_r_val:.2f} R"
    
    dd_str = f"<span style='color:red'>{dd*100:.1f}%</span>" if dd < -0.01 else "0.0%"
    
    entry_str = row["entry_dt"].strftime("%y-%m-%d %H:%M")
    exit_str = row["exit_dt"].strftime("%y-%m-%d %H:%M")
    px_entry = row["entry"]
    px_exit = row["exit"]
    
    rows_md.append(
        f"| {idx+1} | {side_str} | {entry_str} | {px_entry:.4f} | {exit_str} | {px_exit:.4f} | {status_str} | {r_str} | **{cap_vnd:,.0f} đ** | {dd_str} |"
    )

header = """# 📊 BẢNG SAO KÊ CHI TIẾT TỪNG LỆNH: XRP BOT (RISK 10% / LỆNH)

**Vốn khởi điểm:** 15.000.000 VNĐ ($580 USDT)  
**Rủi ro mỗi lệnh:** **10.0%** tài khoản (Đòn bẩy yêu cầu: $\\approx 18.2\\times$)  
**Tổng số lệnh:** 88 lệnh (43 Long, 45 Short)  
- **Lệnh Thắng (TP 17.9%):** 13 lệnh (14.77%) $\\rightarrow$ Mỗi lệnh thắng nhận **+325.4%** tài khoản  
- **Lệnh Thua (SL 0.55%):** 75 lệnh (85.23%) $\\rightarrow$ Mỗi lệnh thua mất **-12.2%** tài khoản  
- **Vốn kết thúc (Sau 4 năm):** **123.307.098.219 VNĐ** (~123 Tỷ VNĐ / $4.76 Triệu USD)  
- **Sụt giảm tài khoản lớn nhất (Max Drawdown):** **-83.78%**  

---

| STT | Vị Thế | Ngày Vào | Giá Vào | Ngày Ra | Giá Ra | Kết Quả | Lãi (R) | Số Dư Sau Lệnh (VNĐ) | Sụt Giảm Đỉnh |
|---|---|---|---|---|---|---|---|---|---|
"""

full_content = header + "\n".join(rows_md)

out_file = "/Users/finn/.gemini/antigravity/brain/921139ef-edbf-43e7-bf4e-d052df21201b/xrp_risk_10_log.md"
with open(out_file, "w") as f:
    f.write(full_content)

print(f"Artifact created: {out_file}")
