import pandas as pd

def calculate_non_compounding_pnl():
    # 1. DOGE 3m (Fixed $200 position)
    # TP 5.0%, SL 15.0%, Maker 0.02%, Taker 0.05%
    # 642 trades (580 Wins, 62 Losses)
    doge_tp = 5.0 / 100
    doge_sl = 15.0 / 100
    doge_win_mult = doge_tp - 0.0002 - 0.0002
    doge_loss_mult = -doge_sl - 0.0002 - 0.0005
    doge_pnl = (580 * 200 * doge_win_mult) + (62 * 200 * doge_loss_mult)
    
    # 2. SOL 5m (Fixed $200 position)
    # TP 5.0%, SL 12.0%
    # 531 trades (455 Wins, 76 Losses)
    sol_tp = 5.0 / 100
    sol_sl = 12.0 / 100
    sol_win_mult = sol_tp - 0.0002 - 0.0002
    sol_loss_mult = -sol_sl - 0.0002 - 0.0005
    sol_pnl = (455 * 200 * sol_win_mult) + (76 * 200 * sol_loss_mult)
    
    # 3. XRP 5m (Fixed $200 position)
    # TP 4.0%, SL 12.0%
    # 577 trades (520 Wins, 57 Losses)
    xrp_tp = 4.0 / 100
    xrp_sl = 12.0 / 100
    xrp_win_mult = xrp_tp - 0.0002 - 0.0002
    xrp_loss_mult = -xrp_sl - 0.0002 - 0.0005
    xrp_pnl = (520 * 200 * xrp_win_mult) + (57 * 200 * xrp_loss_mult)
    
    print("NON-COMPOUNDING PNL (Vốn cố định $200/lệnh)")
    print(f"DOGE 3m: ${doge_pnl:.2f}")
    print(f"SOL 5m: ${sol_pnl:.2f}")
    print(f"XRP 5m: ${xrp_pnl:.2f}")
    return doge_pnl, sol_pnl, xrp_pnl

calculate_non_compounding_pnl()
