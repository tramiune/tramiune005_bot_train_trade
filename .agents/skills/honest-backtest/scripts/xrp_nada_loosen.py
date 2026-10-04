"""Loosen the XRP 5m NW + RSI + Volume signal parameters, exits fixed to the stable high-R:R zone.
Selection uses IN-SAMPLE only (median over the 9 exit settings, not the best exit); OOS is reported.
Usage (repo root): web_app/backend/.venv/bin/python .agents/skills/honest-backtest/scripts/xrp_nada_loosen.py
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
d1 = bt_data.load(SYMBOL, "1m")
sim = H.Sim(d1)
B = H.resample(d1, 5)
c = B["close"].to_numpy()

HS = [6.0, 8.0, 10.0]
MULTS = [2.0, 2.5, 3.0]
RSIS = [(20, 80), (25, 75), (30, 70)]
VOLS = [2.0, 3.0, None]
EXITS = list(itertools.product([0.75, 1.0, 1.5], [8, 10, 12]))  # (SL%, RR)

rows = []
for h, mult, (os_, ob), vm in itertools.product(HS, MULTS, RSIS, VOLS):
    side = X.signals(B, h=h, mult=mult, rsi_os=os_, rsi_ob=ob, vol_mult=vm)
    nsig = int((side != 0).sum())
    is_s, oos_s, all_s, n_tr, wins, dds = [], [], [], [], [], []
    for sl, rr in EXITS:
        T = sim.run(B, side, c * sl / 100, c * sl * rr / 100)
        H.check_trades(T)
        is_s.append(T.loc[T.entry_t < H.SPLIT, "net"].sum())
        oos_s.append(T.loc[T.entry_t >= H.SPLIT, "net"].sum())
        all_s.append(T["net"].sum()); n_tr.append(len(T)); wins.append(int((T.reason == "TP").sum()))
        dds.append(H.metrics(T).get("maxDD%", np.nan))
    is_s, oos_s = np.array(is_s), np.array(oos_s)
    rows.append({"h": h, "mult": mult, "rsi": f"{os_}/{ob}", "vol": "off" if vm is None else vm, "signals": nsig,
                 "trades": int(np.median(n_tr)), "TP_hits": int(np.median(wins)),
                 "IS_med": np.median(is_s), "OOS_med": np.median(oos_s), "ALL_med": np.median(all_s),
                 "exits_pos_both": int(((is_s > 0) & (oos_s > 0)).sum()), "maxDD_med": np.median(dds),
                 "base": (h, mult, os_, vm) == (8.0, 3.0, 20, 2.0)})
R = pd.DataFrame(rows)
R.to_csv(os.path.join(bt_data.ROOT, f"xrp_nada_loosen_{SYMBOL}.csv"), index=False)
print(f"signal settings tested: {len(R)} x {len(EXITS)} exits = {len(R)*len(EXITS)} backtests")
print("\n== BASELINE (your TradingView settings) ==")
print(R[R.base].round(1).to_string(index=False))
print("\n== effect of each parameter (median over all other settings) ==")
for col in ("h", "mult", "rsi", "vol"):
    print(R.groupby(col)[["signals", "trades", "IS_med", "OOS_med", "exits_pos_both"]].median().round(1).to_string(), "\n")
print("== top 15 by IN-SAMPLE median (selection uses IS only) ==")
print(R.sort_values("IS_med", ascending=False).head(15).round(1).to_string(index=False))
print(f"\nsettings positive in IS: {(R.IS_med > 0).sum()} | in OOS: {(R.OOS_med > 0).sum()} | both: {((R.IS_med > 0) & (R.OOS_med > 0)).sum()} of {len(R)}")
