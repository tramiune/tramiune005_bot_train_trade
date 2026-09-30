import re

log_content = """
[ YEAR 2022 ]
[2022-10] Wins:  9 | Losses:  6 
[2022-11] Wins: 10 | Losses: 12 
[2022-12] Wins: 10 | Losses:  3 

[ YEAR 2023 ]
[2023-01] Wins: 12 | Losses: 15 
[2023-02] Wins: 21 | Losses: 11 
[2023-03] Wins: 15 | Losses: 13 
[2023-04] Wins:  9 | Losses:  6 
[2023-05] Wins:  8 | Losses:  5 
[2023-06] Wins: 12 | Losses:  6 
[2023-07] Wins:  6 | Losses:  1 
[2023-08] Wins:  3 | Losses:  4 
[2023-09] Wins:  6 | Losses:  0 
[2023-10] Wins:  7 | Losses:  7 
[2023-11] Wins:  5 | Losses: 10 
[2023-12] Wins: 11 | Losses:  7 

[ YEAR 2024 ]
[2024-01] Wins: 18 | Losses: 12 
[2024-02] Wins:  9 | Losses:  6 
[2024-03] Wins: 12 | Losses: 18 
[2024-04] Wins: 11 | Losses: 11 
[2024-05] Wins: 17 | Losses:  4 
[2024-06] Wins:  4 | Losses:  5 
[2024-07] Wins: 12 | Losses:  8 
[2024-08] Wins: 12 | Losses: 14 
[2024-09] Wins: 18 | Losses:  6 
[2024-10] Wins:  9 | Losses:  4 
[2024-11] Wins: 14 | Losses: 12 
[2024-12] Wins: 11 | Losses: 11 

[ YEAR 2025 ]
[2025-01] Wins: 11 | Losses: 10 
[2025-02] Wins: 16 | Losses: 13 
[2025-03] Wins: 12 | Losses: 11 
[2025-04] Wins: 15 | Losses: 10 
[2025-05] Wins: 15 | Losses:  9 
[2025-06] Wins: 13 | Losses: 12 
[2025-07] Wins:  8 | Losses: 11 
[2025-08] Wins: 13 | Losses: 10 
[2025-09] Wins:  8 | Losses:  7 
[2025-10] Wins: 14 | Losses: 12 
[2025-11] Wins: 21 | Losses:  6 
[2025-12] Wins: 17 | Losses:  7 

[ YEAR 2026 ]
[2026-01] Wins: 10 | Losses:  5 
[2026-02] Wins: 16 | Losses: 12 
[2026-03] Wins: 12 | Losses:  6 
[2026-04] Wins: 11 | Losses:  7 
[2026-05] Wins:  6 | Losses:  4 
[2026-06] Wins: 10 | Losses:  7 
[2026-07] Wins:  6 | Losses:  7 
[2026-08] Wins:  9 | Losses:  4 
[2026-09] Wins: 11 | Losses:  5 
"""

win_profit = 2.50 - 0.04  # $2.46
loss_profit = -3.00 - 0.04 # -$3.04

lines = log_content.strip().split('\n')
md_lines = [
    "# Báo Cáo ETH 5m VWAP Z-Score (Đánh Đều Tay $100/Lệnh)",
    "",
    "**Thiết lập Cố định (Fixed Size):**",
    "- Vị thế mỗi lệnh: **$100 (Đòn bẩy x1)**",
    "- TP 2.5%: Lãi **+$2.46** (Đã trừ phí $0.04)",
    "- SL 3.0%: Lỗ **-$3.04** (Đã cộng phí $0.04)",
    "",
    "| Tháng | Số Lệnh | Win | Loss | Win Rate | Tổng Lãi/Lỗ (USD) |",
    "|-------|---------|-----|------|----------|-------------------|"
]

total_trades = 0
total_wins = 0
total_losses = 0
total_usd = 0.0

for line in lines:
    line = line.strip()
    if not line or line.startswith('[ YEAR'):
        continue
    
    # [2022-10] Wins:  9 | Losses:  6 
    m = re.match(r'\[(.*?)\]\s+Wins:\s+(\d+)\s+\|\s+Losses:\s+(\d+)', line)
    if m:
        month = m.group(1)
        wins = int(m.group(2))
        losses = int(m.group(3))
        
        trades = wins + losses
        total_trades += trades
        total_wins += wins
        total_losses += losses
        
        wr = (wins / trades) * 100 if trades > 0 else 0
        usd_pnl = (wins * win_profit) + (losses * loss_profit)
        total_usd += usd_pnl
        
        sign = "+" if usd_pnl > 0 else ""
        md_lines.append(f"| {month} | {trades} | {wins} | {losses} | {wr:.1f}% | **{sign}{usd_pnl:.2f} $** |")

md_lines.extend([
    "",
    "### 📊 TỔNG KẾT 4 NĂM",
    f"- **Tổng số lệnh:** {total_trades}",
    f"- **Tổng Thắng / Thua:** {total_wins} Wins / {total_losses} Losses",
    f"- **Win Rate Tổng:** {(total_wins/total_trades)*100:.2f}%",
    f"- **Lợi nhuận ròng 4 năm:** **+{total_usd:.2f} USD**"
])

with open('/Users/finn/.gemini/antigravity/brain/921139ef-edbf-43e7-bf4e-d052df21201b/eth_vwap_monthly_report.md', 'w') as f:
    f.write('\n'.join(md_lines))

print("Markdown artifact generated.")
