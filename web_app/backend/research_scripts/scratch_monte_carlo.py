import json
import random

def run_monte_carlo(win_rate, num_trades, initial_capital, risk_pct, reward_pct, runs=10000):
    ruined_count = 0
    
    for _ in range(runs):
        capital = initial_capital
        for _ in range(num_trades):
            if capital <= 0:
                break
                
            risk_amount = capital * risk_pct
            position_size = risk_amount / 0.12 # Because SL is 12%, position size = risk / 0.12
            
            if position_size > capital: # Max position is full capital (no leverage over 1x)
                 position_size = capital
                 risk_amount = position_size * 0.12
                 
            reward_amount = position_size * 0.05 # TP is 5%
            
            if random.random() <= win_rate:
                capital += reward_amount
            else:
                capital -= risk_amount
                
            if capital <= (initial_capital * 0.1): # 90% drawdown = Ruin
                ruined_count += 1
                break
                
    return (ruined_count / runs) * 100

print("=== MÔ PHỎNG MONTE CARLO RỦI RO (10,000 KỊCH BẢN) ===")
print("Giả định: SOL 5m | Win Rate 85.9% | SL 12% | TP 5% | Vốn $400 (10tr)\n")

# Risk 4.5% (The recommended $150 fixed pos -> $18 risk / $400 = 4.5%)
ruin_4 = run_monte_carlo(0.859, 100, 400, 0.045, 0.05)
print(f"Nếu Risk 4.5% tài khoản/lệnh (Bot chạy 100 lệnh): Xác suất Cháy Tài Khoản là {ruin_4:.2f}%")

# Risk 20%
ruin_20 = run_monte_carlo(0.859, 100, 400, 0.20, 0.05)
print(f"Nếu Risk 20% tài khoản/lệnh (Bot chạy 100 lệnh): Xác suất Cháy Tài Khoản là {ruin_20:.2f}%")

ruin_20_year = run_monte_carlo(0.859, 500, 400, 0.20, 0.05)
print(f"Nếu Risk 20% tài khoản/lệnh (Bot chạy 500 lệnh/1 năm): Xác suất Cháy Tài Khoản là {ruin_20_year:.2f}%")

