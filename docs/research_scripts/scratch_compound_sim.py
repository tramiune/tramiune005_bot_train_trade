import math

def simulate_compounding(wins, losses, tp_pct, sl_pct, initial_balance=800, risk_pct=0.30):
    balance = initial_balance
    
    # Calculate optimal trade order (let's do average uniform distribution of losses)
    total_trades = wins + losses
    loss_interval = total_trades / (losses + 1) if losses > 0 else total_trades
    
    maker_fee = 0.0002
    taker_fee = 0.0005
    win_pct_actual = (tp_pct/100) - maker_fee - maker_fee
    loss_pct_actual = (sl_pct/100) + maker_fee + taker_fee
    
    # With risk_pct=0.30 and sl_pct=0.15, Leverage is 2x.
    # When winning, we gain (risk_pct / sl_pct) * tp_pct
    reward_risk_ratio = win_pct_actual / loss_pct_actual
    growth_per_win = risk_pct * reward_risk_ratio
    loss_per_loss = risk_pct # we lose the risk amount
    
    for i in range(total_trades):
        # Evenly space losses
        if (i + 1) % int(loss_interval) == 0 and losses > 0:
            balance = balance * (1 - loss_per_loss)
            losses -= 1
        else:
            balance = balance * (1 + growth_per_win)
            
    return balance

doge = simulate_compounding(580, 62, 5.0, 15.0)
sol = simulate_compounding(455, 76, 5.0, 12.0)
xrp = simulate_compounding(520, 57, 4.0, 12.0)

print(f"COMPOUNDING (Start $800, Risk 30%/Trade)")
print(f"DOGE 3m: ${doge:,.2f}")
print(f"SOL 5m: ${sol:,.2f}")
print(f"XRP 5m: ${xrp:,.2f}")
