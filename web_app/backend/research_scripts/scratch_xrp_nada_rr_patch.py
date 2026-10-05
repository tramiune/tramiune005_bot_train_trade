"""High R:R study for the XRP 5m Nadaraya-Watson + RSI + Volume signals (TP = RR x SL).
Same rules as xrp_nada.py: next-bar-open entry, exits on 1m, SL first, taker+slippage+funding,
one position at a time, IS < 2025-01-01 <= OOS, random-entry baseline.
Usage (repo root): web_app/backend/.venv/bin/python .agents/skills/honest-backtest/scripts/xrp_nada_rr.py
"""
import itertools
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
import bt_data  # noqa: E402
import bt_harness as H  # noqa: E402
import xrp_nada as X  # noqa: E402

pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 40)
SYMBOL = os.environ.get("SYMBOL", "XRPUSDT")

d1 = bt_data.load(SYMBOL, "5m")
sim = H.Sim(d1)
B = d1
side = X.signals(B)
c = B["close"].to_numpy()
k = int((side != 0).sum())
print(f"{SYMBOL}: {k} signals")

SLS = [0.3, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]
RRS = [5, 8, 10, 12, 15, 20]
rows, store = [], {}
for sl, rr in itertools.product(SLS, RRS):
    tp = sl * rr
    T = sim.run(B, side, c * sl / 100, c * tp / 100)
    H.check_trades(T)
    store[(sl, rr)] = T
    cost = 2 * (H.FEE_SIDE + H.SLIP_SIDE)
    be = (sl + cost) / (tp + sl)  # break-even win rate incl. costs (approx, no funding)
    mi, mo, ma = H.metrics(T, None, H.SPLIT), H.metrics(T, H.SPLIT), H.metrics(T)
    rows.append({"sl%": sl, "rr": rr, "tp%": tp, "n": ma["n"], "wins": int((T.reason == "TP").sum()),
                 "win%": ma["win%"], "BE_win%": be * 100, "ev%": ma["ev%"], "ev_R": ma["ev%"] / sl,
                 "sum%": ma["sum%"], "maxDD%": ma["maxDD%"], "IS_n": mi.get("n", 0), "IS_sum": mi.get("sum%"),
                 "OOS_n": mo.get("n", 0), "OOS_sum": mo.get("sum%"), "hold_h": ma["hold_h"], "open": ma["open"]})
R = pd.DataFrame(rows)
print("\n== every SL% x RR cell (sum% = total net % at 1x over the whole period) ==")
print(R.round(2).to_string(index=False))
print("\nsum% net, rows = SL%, cols = RR:")
print(R.pivot(index="sl%", columns="rr", values="sum%").round(1).to_string())
print("\nIS sum% (rows SL%, cols RR):")
print(R.pivot(index="sl%", columns="rr", values="IS_sum").round(1).to_string())
print("\nOOS sum% (rows SL%, cols RR):")
print(R.pivot(index="sl%", columns="rr", values="OOS_sum").round(1).to_string())
print("\nnumber of TP hits (rows SL%, cols RR):")
print(R.pivot(index="sl%", columns="rr", values="wins").to_string())

rng = np.random.default_rng(5)
for sl, rr in [(0.5, 10), (0.75, 10), (1.0, 10), (0.5, 15), (1.0, 15), (0.5, 20)]:
    T = store[(sl, rr)]
    r = T["net"].to_numpy()
    rnd = []
    for _ in range(300):
        rs = np.zeros_like(side)
        rs[rng.choice(np.arange(1000, len(side)), size=k, replace=False)] = rng.choice([-1, 1], size=k)
        rnd.append(sim.run(B, rs, c * sl / 100, c * sl * rr / 100)["net"].sum())
    rnd = np.array(rnd)
    wins = T[T.reason == "TP"]
    print(f"\n-- SL {sl}% RR {rr} (TP {sl*rr:.1f}%): {len(T)} trades, {len(wins)} TP, sum {r.sum():.1f}% | "
          f"random entries: median {np.median(rnd):.1f}%, 95th pct {np.percentile(rnd, 95):.1f}% -> beats {(rnd < r.sum()).mean()*100:.0f}%")
    print("   TP dates:", [pd.to_datetime(t, unit="s").strftime("%Y-%m-%d") for t in wins["entry_t"]])
    print("   per year:", H.per_year(T).to_dict("index"))
    # leave-the-best-win-out: how much depends on single trades
    srt = np.sort(r)[::-1]
    print(f"   sum without the best 1 / 2 / 3 trades: {srt[1:].sum():.1f}% / {srt[2:].sum():.1f}% / {srt[3:].sum():.1f}%")
