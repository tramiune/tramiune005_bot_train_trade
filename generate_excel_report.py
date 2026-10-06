import sys, os, pandas as pd, numpy as np
sys.path.insert(0, os.path.abspath(".agents/skills/honest-backtest/scripts"))
import bt_data, bt_harness as H, xrp_nada as X
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

print("Generating Data...")

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
T_xrp["type"] = np.where(T_xrp["side"] == 1, "LONG", "SHORT")

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
            'type': 'LONG' if pos == 1 else 'SHORT',
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

# 3. MERGE ALL TRADES
cols = ["coin", "type", "entry_dt", "exit_dt", "entry", "exit", "pnl_pct", "net_r", "reason"]
all_trades = pd.concat([T_xrp[cols], T_sol[cols]], ignore_index=True)
all_trades = all_trades.sort_values("exit_dt").reset_index(drop=True)

# 4. SIMULATION WITH 30M TOTAL (15M XRP + 15M SOL) AT 10% RISK PER ACCOUNT
xrp_bal = 15_000_000.0
sol_bal = 15_000_000.0
total_bal = xrp_bal + sol_bal
peak_total = total_bal
max_portfolio_dd = 0.0

records = []

for idx, row in all_trades.iterrows():
    coin = row["coin"]
    net_r = row["net_r"]
    trade_pct = net_r * 0.10
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
    
    records.append({
        "STT": idx + 1,
        "Thời Điểm Đóng Lệnh": row["exit_dt"].strftime("%Y-%m-%d %H:%M"),
        "Bot / Coin": coin,
        "Vị Thế": row["type"],
        "Giá Vào": round(row["entry"], 4),
        "Giá Thoát": round(row["exit"], 4),
        "Kết Quả": "THẮNG (WIN)" if row["pnl_pct"] > 0 else "THUA (LOSS)",
        "Lãi/Lỗ Tiền Tươi (%)": round(row["pnl_pct"], 2),
        "Lợi Nhuận (R)": round(net_r, 2),
        "Lãi/Lỗ Lệnh (VNĐ)": round(pnl_vnd, 0),
        "Số Dư Ví XRP (VNĐ)": round(xrp_bal, 0),
        "Số Dư Ví SOL (VNĐ)": round(sol_bal, 0),
        "TỔNG TÀI SẢN (VNĐ)": round(total_bal, 0),
        "Sụt Giảm Từ Đỉnh (%)": round(port_dd * 100, 2)
    })

df_export = pd.DataFrame(records)

# Save CSV (UTF-8 with BOM for Excel)
csv_file = "/Users/finn/Documents/WEB/tramiune005_bot_train_trade/Bao_Cao_Hop_The_XRP_SOL_30M.csv"
df_export.to_csv(csv_file, index=False, encoding="utf-8-sig")
print(f"Saved CSV: {csv_file}")

# Save Excel with formatting
excel_file = "/Users/finn/Documents/WEB/tramiune005_bot_train_trade/Bao_Cao_Hop_The_XRP_SOL_30M.xlsx"

wb = Workbook()
# Sheet 1: Dashboard
ws_dash = wb.active
ws_dash.title = "Tổng Quan Danh Mục"
ws_dash.views.sheetView[0].showGridLines = True

# Title
ws_dash.merge_cells("A1:G1")
ws_dash["A1"] = "BÁO CÁO ĐỊNH LƯỢNG QUỸ TỰ ĐỘNG QUANT (XRP 5M + SOL 4H)"
ws_dash["A1"].font = Font(name="Calibri", size=16, bold=True, color="1F497D")
ws_dash["A1"].alignment = Alignment(horizontal="center", vertical="center")

ws_dash.merge_cells("A2:G2")
ws_dash["A2"] = "Mô phỏng Dòng tiền Khởi điểm 30.000.000 VNĐ | Rủi ro 10% / Lệnh | Dữ liệu Binance Futures (2022 - 2026)"
ws_dash["A2"].font = Font(name="Calibri", size=11, italic=True, color="595959")
ws_dash["A2"].alignment = Alignment(horizontal="center", vertical="center")

# KPI Summary Cards
kpis = [
    ("TỔNG VỐN BAN ĐẦU", "30,000,000 VNĐ", "15 Tr XRP + 15 Tr SOL"),
    ("TỔNG VỐN CUỐI KỲ", f"{total_bal:,.0f} VNĐ", f"x{total_bal/30e6:,.1f} lần (~{total_bal/1e9:.1f} Tỷ VNĐ)"),
    ("SỤT GIẢM TỐI ĐA (MAX DD)", f"{max_portfolio_dd*100:.2f}%", "Nhờ 2 con bù trừ nhau"),
    ("TỔNG SỐ GIAO DỊCH", f"{len(all_trades)} lệnh", "88 lệnh XRP + 91 lệnh SOL"),
    ("VÍ XRP CUỐI KỲ", f"{xrp_bal:,.0f} VNĐ", f"~{xrp_bal/1e9:.1f} Tỷ VNĐ"),
    ("VÍ SOL CUỐI KỲ", f"{sol_bal:,.0f} VNĐ", f"~{sol_bal/1e9:.1f} Tỷ VNĐ")
]

row_start = 4
for i, (title, val, sub) in enumerate(kpis):
    col = chr(ord('A') + (i % 3) * 2)
    col_next = chr(ord(col) + 1)
    r = row_start + (i // 3) * 4
    
    ws_dash.merge_cells(f"{col}{r}:{col_next}{r}")
    ws_dash.merge_cells(f"{col}{r+1}:{col_next}{r+1}")
    ws_dash.merge_cells(f"{col}{r+2}:{col_next}{r+2}")
    
    ws_dash[f"{col}{r}"] = title
    ws_dash[f"{col}{r}"].font = Font(name="Calibri", size=9, bold=True, color="595959")
    ws_dash[f"{col}{r}"].fill = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid")
    ws_dash[f"{col}{r}"].alignment = Alignment(horizontal="center", vertical="center")
    
    ws_dash[f"{col}{r+1}"] = val
    ws_dash[f"{col}{r+1}"].font = Font(name="Calibri", size=14, bold=True, color="1F497D")
    ws_dash[f"{col}{r+1}"].alignment = Alignment(horizontal="center", vertical="center")
    
    ws_dash[f"{col}{r+2}"] = sub
    ws_dash[f"{col}{r+2}"].font = Font(name="Calibri", size=9, italic=True, color="7F7F7F")
    ws_dash[f"{col}{r+2}"].alignment = Alignment(horizontal="center", vertical="center")

# Sheet 2: Trade Log
ws_trades = wb.create_sheet(title="Nhật Ký 179 Lệnh (Timeline)")
ws_trades.views.sheetView[0].showGridLines = True

headers = list(df_export.columns)
ws_trades.append(headers)

header_fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")

for col_num, header in enumerate(headers, 1):
    cell = ws_trades.cell(row=1, column=col_num)
    cell.fill = header_fill
    cell.font = header_font
    cell.alignment = Alignment(horizontal="center", vertical="center")

win_font = Font(name="Calibri", color="008000", bold=True)
loss_font = Font(name="Calibri", color="C00000")

for row_idx, r_data in enumerate(records, 2):
    ws_trades.append(list(r_data.values()))
    
    # Format currency and percentage
    ws_trades.cell(row=row_idx, column=5).number_format = "#,##0.0000" # Entry
    ws_trades.cell(row=row_idx, column=6).number_format = "#,##0.0000" # Exit
    ws_trades.cell(row=row_idx, column=8).number_format = "+#,##0.00%;-#,##0.00%;0.00%"
    ws_trades.cell(row=row_idx, column=9).number_format = "+#,##0.00;-#,##0.00;0.00"
    ws_trades.cell(row=row_idx, column=10).number_format = "#,##0"
    ws_trades.cell(row=row_idx, column=11).number_format = "#,##0"
    ws_trades.cell(row=row_idx, column=12).number_format = "#,##0"
    ws_trades.cell(row=row_idx, column=13).number_format = "#,##0"
    ws_trades.cell(row=row_idx, column=14).number_format = "0.00%"
    
    if r_data["Kết Quả"] == "THẮNG (WIN)":
        ws_trades.cell(row=row_idx, column=7).font = win_font
        ws_trades.cell(row=row_idx, column=10).font = win_font
    else:
        ws_trades.cell(row=row_idx, column=7).font = loss_font
        ws_trades.cell(row=row_idx, column=10).font = loss_font
        
    ws_trades.cell(row=row_idx, column=13).font = Font(name="Calibri", bold=True)

# Auto fit columns
for ws in [ws_dash, ws_trades]:
    for col in ws.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

wb.save(excel_file)
print(f"Saved Excel: {excel_file}")
