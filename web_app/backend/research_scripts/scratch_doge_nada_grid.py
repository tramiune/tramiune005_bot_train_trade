import itertools
import os
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(".agents/skills/honest-backtest/scripts"))
import bt_data
import bt_harness as H
import xrp_nada as X

def run():
    print("Loading DOGEUSDT 1m data...")
    d1 = bt_data.load("DOGEUSDT", "1m")
    sim = H.Sim(d1)
    
    print("Resampling to 5m & Extracting Nadaraya-Watson Signals...")
    B = H.resample(d1, 5)
    
    # We use the same entry logic as XRP (Nadaraya-Watson lower band touch + RSI oversold + Volume filter)
    # DOGE might need different volume or RSI thresholds, but let's test the baseline first.
    side = X.signals(B)
    c = B["close"].to_numpy()
    k = int((side != 0).sum())
    print(f"DOGEUSDT: {k} signals found.")

    SLS = [0.5, 0.75, 1.0, 1.5, 2.0, 3.0]
    RRS = [5, 8, 10, 12, 15]
    
    print("\nQuét thông số tối ưu cho DOGE (Nadaraya-Watson Bắt đáy):")
    rows = []
    
    for sl, rr in itertools.product(SLS, RRS):
        tp = sl * rr
        T = sim.run(B, side, c * sl / 100, c * tp / 100)
        ma = H.metrics(T)
        
        # H.metrics computes pnl without fees. We deduct fees manually.
        # H.FEE_SIDE = 0.0005, H.SLIP_SIDE = 0.0001 => 0.12% round trip
        cost = 2 * (0.0005 + 0.0001) * 100
        
        wins = int((T.reason == "TP").sum())
        losses = len(T) - wins
        
        # Net R = (Wins * (rr - cost/sl)) - (Losses * (1 + cost/sl))
        # Wait, exact PnL %:
        win_pct = tp - cost
        loss_pct = -sl - cost
        sum_pct = (wins * win_pct) + (losses * loss_pct)
        sum_R = sum_pct / sl if sl > 0 else 0
        
        wr = (wins / len(T) * 100) if len(T) > 0 else 0
        
        rows.append({
            "SL%": sl, "RR": rr, "TP%": tp, "Trades": len(T),
            "Wins": wins, "WinRate%": wr, "Net_R": sum_R
        })
        
    R_df = pd.DataFrame(rows)
    print("\n--- BẢNG KẾT QUẢ NET R TỪNG CẤU HÌNH ---")
    print(R_df.pivot(index="SL%", columns="RR", values="Net_R").round(1).to_string())
    
    print("\n--- BẢNG KẾT QUẢ WIN RATE (%) TỪNG CẤU HÌNH ---")
    print(R_df.pivot(index="SL%", columns="RR", values="WinRate%").round(1).to_string())

run()
