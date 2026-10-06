import sys, os
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.abspath(".agents/skills/honest-backtest/scripts"))
import bt_data
import bt_harness as H

def supertrend(h, l, c, period=14, mult=5.0):
    tr1 = h - l
    tr2 = np.abs(h - np.roll(c, 1))
    tr3 = np.abs(l - np.roll(c, 1))
    tr = np.maximum(tr1, np.maximum(tr2, tr3))
    tr[0] = tr1[0]
    
    atr = np.zeros(len(c))
    atr[0] = tr[0]
    for i in range(1, len(c)):
        atr[i] = (atr[i-1] * (period - 1) + tr[i]) / period
        
    hl2 = (h + l) / 2
    basic_ub = hl2 + mult * atr
    basic_lb = hl2 - mult * atr
    
    final_ub = np.zeros(len(c))
    final_lb = np.zeros(len(c))
    trend = np.ones(len(c))
    
    for i in range(1, len(c)):
        if basic_ub[i] < final_ub[i-1] or c[i-1] > final_ub[i-1]:
            final_ub[i] = basic_ub[i]
        else:
            final_ub[i] = final_ub[i-1]
            
        if basic_lb[i] > final_lb[i-1] or c[i-1] < final_lb[i-1]:
            final_lb[i] = basic_lb[i]
        else:
            final_lb[i] = final_lb[i-1]
            
        if trend[i-1] == 1 and c[i] < final_lb[i]:
            trend[i] = -1
        elif trend[i-1] == -1 and c[i] > final_ub[i]:
            trend[i] = 1
        else:
            trend[i] = trend[i-1]
            
    return trend

def test_supertrend(coin, length=14, mult=5.0):
    d1 = bt_data.load(coin, "1m")
    sim = H.Sim(d1)
    B = H.resample(d1, 240) # 4H
    
    c = B["close"].to_numpy()
    h = B["high"].to_numpy()
    l = B["low"].to_numpy()
    
    trend = supertrend(h, l, c, length, mult)
    
    side = np.zeros(len(B), dtype=int)
    for i in range(1, len(trend)):
        if trend[i] == 1 and trend[i-1] == -1:
            side[i] = 1
        elif trend[i] == -1 and trend[i-1] == 1:
            side[i] = -1
            
    ct = B["close_time"].to_numpy()
    idx = np.nonzero(side)[0]
    trades, pos, e, et = [], 0, 0.0, 0
    for bi in idx:
        s = int(side[bi])
        j = np.searchsorted(sim.t, ct[bi])
        if j >= sim.n or sim.t[j] != ct[bi]: continue
        px = sim.o[j]
        if pos != 0:
            gross = pos * (px / e - 1) * 100
            trades.append({'exit_t': int(sim.t[j]), 'gross': gross, 'pos': pos})
        pos, e, et = s, px, int(sim.t[j])
        
    T = pd.DataFrame(trades)
    cost = 0.12 # 0.12% round trip
    T['pnl'] = T['gross'] - cost
    
    wins = len(T[T['pnl'] > 0])
    losses = len(T[T['pnl'] <= 0])
    wr = wins / len(T) * 100
    
    total_pnl = T['pnl'].sum()
    
    avg_loss = abs(T[T['pnl'] < 0]['pnl'].mean())
    if avg_loss == 0 or pd.isna(avg_loss): avg_loss = 5.0
    
    T['r_val'] = T['pnl'] / avg_loss
    net_r = T['r_val'].sum()
    
    print(f"[{coin}] Cấu hình Supertrend (14, {mult}) trên khung 4H:")
    print(f"- Tổng số lệnh: {len(T)}")
    print(f"- Số lệnh Thắng: {wins} | Thua: {losses} (Win Rate: {wr:.1f}%)")
    print(f"- Mức Cắt lỗ trung bình / lệnh: -{avg_loss:.2f}%")
    print(f"- Tổng Lãi Ròng gộp (Tiền tươi, không đòn bẩy): +{total_pnl:.2f}%")
    print(f"- Tổng Lợi Nhuận quy ra (R): +{net_r:.2f} R\n")

print("Đang chạy Backtest so sánh SOL và DOGE...")
test_supertrend("SOLUSDT")
test_supertrend("DOGEUSDT")
