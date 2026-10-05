import random

def run_monte_carlo(win_rate, num_trades, initial_capital, risk_pct, runs=10000):
    ruined_count = 0
    total_final = 0
    
    for _ in range(runs):
        capital = initial_capital
        for _ in range(num_trades):
            if capital <= 0:
                break
                
            risk_amount = capital * risk_pct
            position_size = risk_amount / 0.12 # Leverage is implicitly used
            reward_amount = position_size * 0.05
            
            if random.random() <= win_rate:
                capital += reward_amount
            else:
                capital -= risk_amount
                
            if capital <= (initial_capital * 0.1): # 90% drawdown = Ruin
                ruined_count += 1
                break
        
        total_final += capital
                
    return (ruined_count / runs) * 100, (total_final / runs)

print("=== MÔ PHỎNG MONTE CARLO - RỦI RO 20% (Có dùng Margin/Đòn bẩy) ===")
ruin_20, avg_20 = run_monte_carlo(0.859, 100, 400, 0.20)
print(f"Chạy 100 lệnh: Xác suất Cháy = {ruin_20:.2f}% | Vốn trung bình = ${avg_20:.2f}")

ruin_20_year, avg_20_year = run_monte_carlo(0.859, 500, 400, 0.20)
print(f"Chạy 500 lệnh: Xác suất Cháy = {ruin_20_year:.2f}% | Vốn trung bình = ${avg_20_year:.2f}")

