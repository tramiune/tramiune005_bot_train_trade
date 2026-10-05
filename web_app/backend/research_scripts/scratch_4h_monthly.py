import itertools
import os
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(".agents/skills/honest-backtest/scripts"))
import bt_data
import bt_harness as H
from strategy_signals import sig_donchian

pd.set_option("display.width", 250)
sym = "DOGEUSDT"

d1 = bt_data.load(sym, "1m")
sim = H.Sim(d1)
B = H.resample(d1, 240)
A = H.atr(B, 14).to_numpy()

n = 100
slm, tpm = 1.5, 3.0
sg = np.asarray(sig_donchian(B, n)); sg[:210] = 0
T = sim.run(B, sg, A * slm, A * tpm)

# T is a pandas DataFrame with 'entry_t', 'exit_t', 'net' (percentage return), etc.
T['entry_date'] = pd.to_datetime(T['entry_t'], unit='s')
T['year'] = T['entry_date'].dt.year
T['month'] = T['entry_date'].dt.month

monthly_stats = T.groupby(['year', 'month']).agg(
    trades=('net', 'count'),
    wins=('net', lambda x: (x > 0).sum()),
    pnl=('net', 'sum')
).reset_index()

print("Year-Month | Trades | Wins | PnL (%)")
print("-" * 40)
for _, row in monthly_stats.iterrows():
    print(f"{int(row['year'])}-{int(row['month']):02d}    | {int(row['trades']):6d} | {int(row['wins']):4d} | {row['pnl']:7.2f}%")

print("-" * 40)
print(f"Total Trades: {len(T)}")
print(f"Total PnL: {T['net'].sum():.2f}%")
