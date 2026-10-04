"""Hour-of-day filter for the DOGE 3m squeeze strategies, tested honestly.
Variants (one position at a time, taker + slippage + funding):
  contra 5/15 (live bot), contra 5/5, follow 5/5, 1d-EMA20 direction 5/5.
Checks:
  1) per-hour (UTC, also shown in Vietnam time UTC+7) net results in-sample (<2025) vs out-of-sample;
     correlation of the 24 hourly results between the two periods (near 0 = hour pattern is noise)
  2) "pick good hours on IS, apply to OOS"
  3) walk-forward: every quarter from 2024-01 keep only hours whose PAST trades (finished before the
     quarter) have positive average net (min 8 trades), simulate the quarter one position at a time
  4) coarse sessions (Asia / Europe / US / late) instead of single hours
Usage (repo root): web_app/backend/.venv/bin/python .agents/skills/honest-backtest/scripts/hour_filter.py
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
import bt_data  # noqa: E402
import bt_harness as H  # noqa: E402
from strategy_signals import sig_squeeze  # noqa: E402

pd.set_option("display.width", 250)
d1 = bt_data.load("DOGEUSDT", "1m")
sim = H.Sim(d1)
B = H.resample(d1, 3)
c = B["close"].to_numpy()
ct = B["close_time"].to_numpy()
hour = (ct // 3600) % 24
brk = np.asarray(sig_squeeze(B, follow=True)); brk[:200] = 0
D1 = H.resample(d1, 1440); D1["v"] = H.ema(D1["close"], 20)
ema1d = pd.merge_asof(B[["close_time"]], D1[["close_time", "v"]], on="close_time", direction="backward")["v"].to_numpy()

VARIANTS = {
    "contra 5/15 (live)": (-brk, 0.15, 0.05),
    "contra 5/5": (-brk, 0.05, 0.05),
    "follow 5/5": (brk, 0.05, 0.05),
    "1dEMA20 dir 5/5": (np.where(brk != 0, np.sign(np.nan_to_num(c - ema1d)), 0).astype(int), 0.05, 0.05),
}
SESS = {"Asia 0-8 UTC (7-15h VN)": range(0, 8), "Europe 8-13 UTC (15-20h VN)": range(8, 13),
        "US 13-21 UTC (20-04h VN)": range(13, 21), "Late 21-24 UTC (04-07h VN)": range(21, 24)}
WF0 = pd.Timestamp("2024-01-01", tz="UTC").timestamp()
quarters = pd.date_range("2024-01-01", "2026-10-01", freq="QS", tz="UTC")

for name, (side0, sl, tp) in VARIANTS.items():
    side0 = np.asarray(side0)
    T = sim.run(B, side0, c * sl, c * tp); H.check_trades(T)
    T["hour"] = (T.entry_t // 3600) % 24
    I, O = T[T.entry_t < H.SPLIT], T[T.entry_t >= H.SPLIT]
    hi = I.groupby("hour").net.agg(["size", "sum"]).reindex(range(24), fill_value=0)
    ho = O.groupby("hour").net.agg(["size", "sum"]).reindex(range(24), fill_value=0)
    corr = np.corrcoef(hi["sum"] / hi["size"].clip(lower=1), ho["sum"] / ho["size"].clip(lower=1))[0, 1]
    print(f"\n================ {name}: all hours IS {I.net.sum():+.0f}% ({len(I)} tr) | OOS {O.net.sum():+.0f}% ({len(O)} tr)")
    tab = pd.DataFrame({"VN": [(h + 7) % 24 for h in range(24)], "IS_n": hi["size"], "IS_sum": hi["sum"].round(0),
                        "OOS_n": ho["size"], "OOS_sum": ho["sum"].round(0)})
    print("per hour (index = UTC hour):\n" + tab.T.to_string())
    print(f"correlation of hourly avg result IS vs OOS: {corr:+.2f}  (near 0 => hour pattern does not repeat)")

    # 2) pick hours positive in IS, apply everywhere (sequential re-simulation)
    good = set(hi.index[hi["sum"] > 0])
    s2 = np.where(np.isin(hour, list(good)), side0, 0)
    T2 = sim.run(B, s2, c * sl, c * tp)
    print(f"IS-picked hours {sorted((h + 7) % 24 for h in good)} (VN): IS {T2[T2.entry_t<H.SPLIT].net.sum():+.0f}% "
          f"({(T2.entry_t<H.SPLIT).sum()} tr) | OOS {T2[T2.entry_t>=H.SPLIT].net.sum():+.0f}% ({(T2.entry_t>=H.SPLIT).sum()} tr)")

    # 3) walk-forward hour selection
    s3 = np.zeros_like(side0)
    for q0, q1 in zip(quarters, list(quarters[1:]) + [pd.Timestamp("2027-01-01", tz="UTC")]):
        past = T[T.exit_t < q0.timestamp()]
        g = past.groupby("hour").net.agg(["size", "mean"])
        keep = g.index[(g["size"] >= 8) & (g["mean"] > 0)]
        m = (ct >= q0.timestamp()) & (ct < q1.timestamp()) & np.isin(hour, list(keep))
        s3[m] = side0[m]
    T3 = sim.run(B, s3, c * sl, c * tp)
    T3 = T3[T3.entry_t >= WF0]; T0 = T[T.entry_t >= WF0]
    print(f"walk-forward hours, 2024-01 -> now: {T3.net.sum():+.0f}% ({len(T3)} tr, {T3.net.mean() if len(T3) else 0:+.3f}%/tr) "
          f"vs no filter {T0.net.sum():+.0f}% ({len(T0)} tr, {T0.net.mean():+.3f}%/tr)")

    # 4) sessions
    out = []
    for sname, hrs in SESS.items():
        s4 = np.where(np.isin(hour, list(hrs)), side0, 0)
        T4 = sim.run(B, s4, c * sl, c * tp)
        out.append(f"{sname}: IS {T4[T4.entry_t<H.SPLIT].net.sum():+.0f}% / OOS {T4[T4.entry_t>=H.SPLIT].net.sum():+.0f}% ({len(T4)} tr)")
    print("sessions only: " + " | ".join(out))
