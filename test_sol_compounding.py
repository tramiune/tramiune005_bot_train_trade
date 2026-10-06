import sys, os, pandas as pd, numpy as np
sys.path.insert(0, os.path.abspath(".agents/skills/honest-backtest/scripts"))
import bt_data, bt_harness as H

sol = bt_data.load("SOLUSDT", "1m")
sim = H.Sim(sol)
B = H.resample(sol, 240) # 4H
c, h, l = B["close"].to_numpy(), B["high"].to_numpy(), B["low"].to_numpy()
ct = B["close_time"].to_numpy()

period, mult = 17, 4.3

tr1 = h - l
tr2 = np.abs(h - np.roll(c, 1))
tr3 = np.abs(l - np.roll(c, 1))
tr = np.maximum(tr1, np.maximum(tr2, tr3))
tr[0] = tr1[0]
atr = np.zeros(len(c))
atr[0] = tr[0]
for i in range(1, len(c)): atr[i] = (atr[i-1] * (period - 1) + tr[i]) / period

hl2 = (h + l) / 2
basic_ub = hl2 + mult * atr
basic_lb = hl2 - mult * atr
final_ub = np.zeros(len(c))
final_lb = np.zeros(len(c))
trend = np.ones(len(c))

for i in range(1, len(c)):
    if basic_ub[i] < final_ub[i-1] or c[i-1] > final_ub[i-1]: final_ub[i] = basic_ub[i]
    else: final_ub[i] = final_ub[i-1]
        
    if basic_lb[i] > final_lb[i-1] or c[i-1] < final_lb[i-1]: final_lb[i] = basic_lb[i]
    else: final_lb[i] = final_lb[i-1]
        
    if trend[i-1] == 1 and c[i] < final_lb[i]: trend[i] = -1
    elif trend[i-1] == -1 and c[i] > final_ub[i]: trend[i] = 1
    else: trend[i] = trend[i-1]

side = np.zeros(len(B), dtype=int)
for i in range(1, len(trend)):
    if trend[i] == 1 and trend[i-1] == -1: side[i] = 1
    elif trend[i-1] == -1 and trend[i-1] == 1: side[i] = -1

idx = np.nonzero(side)[0]
trades, pos, e, et = [], 0, 0.0, 0
initial_sl = 0.0

for bi in idx:
    s = int(side[bi])
    j = np.searchsorted(sim.t, ct[bi])
    if j >= sim.n or sim.t[j] != ct[bi]: continue
    px = sim.o[j]
    
    if pos != 0:
        gross = pos * (px / e - 1) * 100
        pnl = gross - 0.12 # fee
        true_r = pnl / initial_sl if initial_sl > 0.5 else pnl / 5.0
        trades.append({
            'entry_t': et,
            'exit_t': int(sim.t[j]),
            'entry_px': e,
            'exit_px': px,
            'type': 'LONG 📈' if pos == 1 else 'SHORT 📉',
            'pnl_pct': pnl,
            'sl_pct': initial_sl,
            'net_r': true_r
        })
    pos, e, et = s, px, int(sim.t[j])
    if pos == 1: initial_sl = (px - final_lb[bi]) / px * 100
    else: initial_sl = (final_ub[bi] - px) / px * 100

T = pd.DataFrame(trades)
print("Total trades extracted:", len(T))

# Test with 10% risk
cap = 15_000_000.0
peak = cap
max_dd = 0.0

for idx, row in T.iterrows():
    trade_pct = row['net_r'] * 0.10 # 10% risk
    # protect against extreme blowup if single trade loss > 100%
    if trade_pct <= -1.0: trade_pct = -0.99
    cap = cap * (1 + trade_pct)
    peak = max(peak, cap)
    dd = (cap - peak) / peak
    max_dd = min(max_dd, dd)

print(f"Final Capital at 10% risk: {cap:,.0f} VND")
print(f"Max Drawdown: {max_dd*100:.2f}%")
print(f"Wins: {(T['pnl_pct'] > 0).sum()} | Losses: {(T['pnl_pct'] <= 0).sum()}")
