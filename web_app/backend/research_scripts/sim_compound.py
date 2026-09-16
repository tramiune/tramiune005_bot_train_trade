def sim(risk_pct):
    balance = 100.0
    wins = 8
    losses = 14
    rr = 15.0
    
    # Simulate worst-case sequence first: 4 losses, then a win, etc.
    # We just do a simple average compounding multiplier for now.
    # Multiplier per win = (1 + risk_pct * 15)
    # Multiplier per loss = (1 - risk_pct)
    
    final_mult = ((1 + risk_pct * rr) ** wins) * ((1 - risk_pct) ** losses)
    return balance * final_mult

for r in [0.02, 0.05, 0.10, 0.15, 0.20, 0.32]:
    print(f"Risk {r*100:g}% -> ${sim(r):,.2f}")
