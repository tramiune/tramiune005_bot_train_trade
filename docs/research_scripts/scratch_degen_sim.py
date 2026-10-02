import random

def run_monte_carlo(win_rate, num_trades, initial_capital, risk_pct, runs=10000):
    ruined_count = 0
    total_final = 0
    max_capital_seen = 0
    
    for _ in range(runs):
        capital = initial_capital
        peak = capital
        for _ in range(num_trades):
            if capital <= 0:
                break
                
            risk_amount = capital * risk_pct
            position_size = risk_amount / 0.12 # Leverage
            reward_amount = position_size * 0.05
            
            if random.random() <= win_rate:
                capital += reward_amount
            else:
                capital -= risk_amount
                
            if capital > peak:
                peak = capital
                
            if capital <= (initial_capital * 0.1): # 90% drawdown = Ruin
                ruined_count += 1
                break
        
        total_final += capital
        if peak > max_capital_seen:
            max_capital_seen = peak
                
    return (ruined_count / runs) * 100, (total_final / runs), max_capital_seen

print("=== MÔ PHỎNG DEGEN MODE - VỐN $800 (20 TRIỆU) ===")

print("\n1. Mức cược Bạo Chúa (Risk 30% / lệnh):")
ruin_30, avg_30, max_30 = run_monte_carlo(0.859, 100, 800, 0.30)
print(f"Xác suất cháy: {ruin_30:.2f}% | Lãi trung bình sau 100 lệnh: ${avg_30:,.0f} | Đỉnh cao nhất mô phỏng: ${max_30:,.0f}")

print("\n2. Mức cược Khô Máu (Risk 40% / lệnh):")
ruin_40, avg_40, max_40 = run_monte_carlo(0.859, 100, 800, 0.40)
print(f"Xác suất cháy: {ruin_40:.2f}% | Lãi trung bình sau 100 lệnh: ${avg_40:,.0f} | Đỉnh cao nhất mô phỏng: ${max_40:,.0f}")

print("\n3. Mức cược Tối Đa theo Kelly (Risk 50% / lệnh):")
ruin_50, avg_50, max_50 = run_monte_carlo(0.859, 100, 800, 0.50)
print(f"Xác suất cháy: {ruin_50:.2f}% | Lãi trung bình sau 100 lệnh: ${avg_50:,.0f} | Đỉnh cao nhất mô phỏng: ${max_50:,.0f}")

