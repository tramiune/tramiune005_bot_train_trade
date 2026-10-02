import json

with open('sol_5m_monthly.json', 'r') as f:
    data = json.load(f)

print("| Tháng | Thắng - Thua | Win Rate (%) | Lợi Nhuận ($) |")
print("|-------|--------------|--------------|---------------|")

total_w = 0
total_l = 0
total_pnl = 0

for m in sorted(data.keys()):
    w = data[m]['wins']
    l = data[m]['losses']
    pnl = data[m]['pnl']
    wr = (w / (w+l) * 100) if (w+l) > 0 else 0
    total_w += w
    total_l += l
    total_pnl += pnl
    print(f"| {m} | {w}W - {l}L | {wr:.1f}% | **${pnl:+.2f}** |")
    
print(f"| **TỔNG** | **{total_w}W - {total_l}L** | **{total_w/(total_w+total_l)*100:.1f}%** | **${total_pnl:+.2f}** |")
