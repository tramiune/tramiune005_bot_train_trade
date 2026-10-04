"""Strategy search on DOGEUSDT futures with the honest harness.
Selection is done on IN-SAMPLE only (before 2025-01-01); out-of-sample is only reported.
Usage (VPS, web_app/backend, venv on):  PYTHONPATH=.:/tmp python /tmp/strategy_search.py
"""
import itertools
import sys
import time

import numpy as np
import pandas as pd

import bt_harness as H

pd.set_option("display.width", 220)
pd.set_option("display.max_columns", 30)
t0 = time.time()
df3, info = H.load_3m()
print("DATA", info, flush=True)
sim = H.Sim(df3)


from strategy_signals import sig_bb, sig_donchian, sig_ema, sig_rsi, sig_squeeze  # noqa: E402

# ---------------------------------------------------------------- 0) harness self-check vs the known result
B3 = H.resample(df3, 3)
s0 = sig_squeeze(B3, follow=False); s0[:200] = 0
c0 = B3["close"].to_numpy()
T0 = sim.run(B3, s0, c0 * 0.15, c0 * 0.05)
H.check_trades(T0)
closed = T0[T0.reason != "OPEN"]
print(f"SELF-CHECK DOGE_3M_DEGEN 5/15: trades={len(closed)} (+{(T0.reason=='OPEN').sum()} open) "
      f"win={(closed.gross>0).mean()*100:.1f}%  [expected ~374 / ~75.7%]", flush=True)
print(pd.DataFrame([H.metrics(T0), H.metrics(T0, None, H.SPLIT), H.metrics(T0, H.SPLIT)],
                   index=["ALL", "IS", "OOS"]).round(2).to_string(), flush=True)

# ---------------------------------------------------------------- 1) grid
TFS = {"15m": 15, "1h": 60, "4h": 240}
TREND_EXITS = list(itertools.product([1.5, 2, 3], [2, 3, 5, 8]))   # (SL xATR, TP xATR)
MR_EXITS = list(itertools.product([1.5, 2, 3], [1, 1.5, 2, 3]))
STRATS = []
for n in (20, 55, 100):
    STRATS.append((f"donchian{n}", lambda B, n=n: sig_donchian(B, n), TREND_EXITS))
for f, s in ((9, 21), (20, 50), (50, 200)):
    STRATS.append((f"ema{f}/{s}", lambda B, f=f, s=s: sig_ema(B, f, s), TREND_EXITS))
for lo, tr in itertools.product((30, 25, 20), (False, True)):
    STRATS.append((f"rsi{lo}{'_t' if tr else ''}", lambda B, lo=lo, tr=tr: sig_rsi(B, lo, tr), MR_EXITS))
for tr in (False, True):
    STRATS.append((f"bb{'_t' if tr else ''}", lambda B, tr=tr: sig_bb(B, tr), MR_EXITS))
for fo in (True, False):
    STRATS.append((f"squeeze_{'follow' if fo else 'contra'}", lambda B, fo=fo: sig_squeeze(B, fo), TREND_EXITS + MR_EXITS))

rows, store = [], {}
for tfn, mins in TFS.items():
    B = H.resample(df3, mins)
    A = H.atr(B, 14).to_numpy()
    for name, fn, exits in STRATS:
        sg = np.asarray(fn(B)); sg[:210] = 0
        for slm, tpm in exits:
            T = sim.run(B, sg, A * slm, A * tpm)
            H.check_trades(T)
            key = (tfn, name, slm, tpm)
            store[key] = T
            mi, mo = H.metrics(T, None, H.SPLIT), H.metrics(T, H.SPLIT)
            rows.append({"tf": tfn, "strat": name, "sl": slm, "tp": tpm,
                         "IS_n": mi.get("n", 0), "IS_win": mi.get("win%"), "IS_ev": mi.get("ev%"), "IS_sum": mi.get("sum%"),
                         "IS_dd": mi.get("maxDD%"), "IS_pf": mi.get("PF"),
                         "OOS_n": mo.get("n", 0), "OOS_win": mo.get("win%"), "OOS_ev": mo.get("ev%"), "OOS_sum": mo.get("sum%"),
                         "OOS_dd": mo.get("maxDD%"), "OOS_pf": mo.get("PF")})
    print(f"  done {tfn}  ({time.time()-t0:.0f}s)", flush=True)

R = pd.DataFrame(rows)
R.to_csv("/tmp/strategy_search_results.csv", index=False)
print(f"\nCOMBOS TESTED: {len(R)}  (expect some to look good by pure luck)")
print(f"IS profitable: {(R.IS_sum>0).sum()}  |  OOS profitable: {(R.OOS_sum>0).sum()}  |  both: {((R.IS_sum>0)&(R.OOS_sum>0)).sum()}")

# selection on IS only: enough trades, positive EV after costs; rank by IS PF
cand = R[(R.IS_n >= 60) & (R.IS_ev > 0)].sort_values("IS_pf", ascending=False)
print("\n== TOP 15 chosen on IN-SAMPLE only (IS_n>=60, IS_ev>0, ranked by IS PF) -> their OUT-OF-SAMPLE ==")
print(cand.head(15).round(2).to_string(index=False))

# robustness: per strategy/tf, share of exit combos that are positive in both halves
g = R.groupby(["tf", "strat"]).apply(lambda d: pd.Series({
    "combos": len(d), "pos_IS": (d.IS_sum > 0).mean() * 100, "pos_OOS": (d.OOS_sum > 0).mean() * 100,
    "pos_both": ((d.IS_sum > 0) & (d.OOS_sum > 0)).mean() * 100,
    "med_IS_ev": d.IS_ev.median(), "med_OOS_ev": d.OOS_ev.median()}))
print("\n== ROBUSTNESS per strategy (share of exit settings profitable; median EV per trade, % net) ==")
print(g.sort_values("pos_both", ascending=False).round(2).to_string())
print(f"\nTOTAL TIME {time.time()-t0:.0f}s")
