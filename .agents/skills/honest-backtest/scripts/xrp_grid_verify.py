"""Verify the XRP 5m NW+RSI+Volume "ultra / extreme grid" claims (research_scripts/scratch_xrp_ultra_grid.py,
scratch_xrp_extreme_grid.py, scratch_xrp_top1_log.py, scratch_xrp_streak_analysis.py).

Those scripts pick the best cell of a ~7,700-run grid on the WHOLE history and book every TP/SL at the fixed
percentage with 0.12% round-trip cost (no slippage on gaps, no funding). Here:
  A) reproduce the claimed cells with their accounting vs honest accounting (Sim net: gap fills, 0.14% cost, funding)
  B) selection bias: choose on in-sample (< 2025) only, look at out-of-sample; IS-vs-OOS rank correlation
  C) random-entry baseline and leave-best-trades-out for the claimed cell
  D) same cell on DOGE / SOL / ETH / BTC
Usage (repo root): web_app/backend/.venv/bin/python .agents/skills/honest-backtest/scripts/xrp_grid_verify.py
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
COST = 2 * (H.FEE_SIDE + H.SLIP_SIDE)


def load(sym):
    d1 = bt_data.load(sym, "1m")
    return H.Sim(d1), H.resample(d1, 5)


def stats(T, sl):
    """R units = net % / SL % (fixed-fraction risk sizing)."""
    if len(T) == 0:
        return {"n": 0}
    r = T["net"].to_numpy() / sl
    isr = T["entry_t"].to_numpy() < H.SPLIT
    eq = np.cumsum(r)
    dd = (np.maximum.accumulate(eq) - eq).max()
    streak = cur = 0
    for x in r:
        cur = cur + 1 if x <= 0 else 0
        streak = max(streak, cur)
    srt = np.sort(r)[::-1]
    return {"n": len(T), "TP": int((T.reason == "TP").sum()), "win%": (T.reason == "TP").mean() * 100,
            "R": r.sum(), "IS_R": r[isr].sum(), "OOS_R": r[~isr].sum(), "IS_n": int(isr.sum()),
            "maxDD_R": dd, "lose_streak": streak, "R_wo_best3": srt[3:].sum()}


def their_R(T, sl, tp):
    """Accounting used by the scratch scripts: every TP = tp-0.12, everything else = -sl-0.12."""
    c = 2 * (0.0005 + 0.0001) * 100
    w = int((T.reason == "TP").sum())
    return (w * (tp - c) + (len(T) - w) * (-sl - c)) / sl


sim, B = load("XRPUSDT")
c = B["close"].to_numpy()

# ---------------------------------------------------------------- A) claimed cells
print("== A) claimed cells: their accounting vs honest ==")
CLAIMS = [  # (rsi, vol, band, sl, tp, label)
    (20, 2.5, 3.0, 0.5, 15.0, "streak_analysis 'Vua Ky Luc +218R'"),
    (20, 2.5, 3.0, 0.75, 15.0, "top1_log 'TOP 1'"),
    (20, 2.0, 3.0, 1.0, 10.0, "original user script, SL1 RR10 (our earlier study)"),
]
claimT = {}
for rs, vm, m, sl, tp, lab in CLAIMS:
    side = X.signals(B, h=8.0, mult=m, rsi_os=rs, rsi_ob=100 - rs, vol_mult=vm)
    T = sim.run(B, side, c * sl / 100, c * tp / 100)
    H.check_trades(T)
    claimT[lab] = (T, sl, tp, side)
    s = stats(T, sl)
    print(f"\n-- {lab}: RSI {rs}/{100-rs}, vol<{vm}x, band {m}, SL {sl}% TP {tp}% (RR {tp/sl:.0f}), "
          f"{int((side != 0).sum())} signals")
    print(f"   their R: {their_R(T, sl, tp):.1f} | honest: {pd.Series(s).round(1).to_dict()}")
    print("   reasons:", T.reason.value_counts().to_dict(), "| mean hold h:", round(T.hold_h.mean(), 1),
          "| SL fills worse than SL (gaps):", int(((T.reason == "SL") & (T.gross < -sl - 1e-9)).sum()))
    print("   per year (net %):", H.per_year(T).to_dict("index"))
    print("   TP dates:", [pd.to_datetime(t, unit="s").strftime("%Y-%m-%d") for t in T[T.reason == "TP"].entry_t])

# ---------------------------------------------------------------- B) grid, IS selection
print("\n== B) the same grids, honest accounting, selection on IS only ==")
ultra = list(itertools.product([5, 10, 15, 18, 20, 22, 25, 30], [1.5, 2.0, 2.5, 3.0, 3.5, 4.0],
                               [2.5, 3.0, 3.5, 4.0], [0.5, 0.75, 1.0, 1.25, 1.5, 2.0], [5, 8, 10, 12, 15, 20]))
extreme = list(itertools.product([15, 20], [2.5, 3.0, 4.0, 5.0], [3.0, 3.5, 4.0, 4.5],
                                 [0.2, 0.3, 0.4, 0.5, 0.75], [10, 15, 20, 25, 30]))
cells = sorted(set(ultra) | set(extreme))
print(f"{len(cells)} cells")
rows, sig_cache = [], {}
for rs, vm, m, sl, rr in cells:
    key = (rs, vm, m)
    if key not in sig_cache:
        sig_cache[key] = X.signals(B, h=8.0, mult=m, rsi_os=rs, rsi_ob=100 - rs, vol_mult=vm)
    side = sig_cache[key]
    if (side == 1).sum() < 10:  # same filter as the scratch scripts
        continue
    T = sim.run(B, side, c * sl / 100, c * sl * rr / 100)
    if len(T) < 10:
        continue
    s = stats(T, sl)
    rows.append({"rsi": rs, "vol": vm, "band": m, "sl": sl, "rr": rr, "their_R": their_R(T, sl, sl * rr), **s})
G = pd.DataFrame(rows)
G.to_csv(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "data", "xrp_grid_verify.csv"), index=False)
print(f"{len(G)} cells evaluated")
print(f"positive full: {(G.R > 0).mean()*100:.0f}% | positive IS: {(G.IS_R > 0).mean()*100:.0f}% | "
      f"positive OOS: {(G.OOS_R > 0).mean()*100:.0f}% | both: {((G.IS_R > 0) & (G.OOS_R > 0)).mean()*100:.0f}%")
print(f"Spearman IS_R vs OOS_R over all cells: {G.IS_R.rank().corr(G.OOS_R.rank()):.2f}")
cols = ["rsi", "vol", "band", "sl", "rr", "n", "TP", "win%", "their_R", "R", "IS_R", "OOS_R", "maxDD_R",
        "lose_streak", "R_wo_best3"]
print("\nTop 10 by FULL-history honest R (= what the scratch scripts do; look-ahead selection):")
print(G.sort_values("R", ascending=False).head(10)[cols].round(1).to_string(index=False))
top_is = G.sort_values("IS_R", ascending=False)
print("\nTop 10 by IS R only, with their OOS:")
print(top_is.head(10)[cols].round(1).to_string(index=False))
for k in (1, 10, 50):
    print(f"IS top-{k}: mean OOS R {top_is.head(k).OOS_R.mean():.1f} vs all cells mean OOS R {G.OOS_R.mean():.1f}, "
          f"median {G.OOS_R.median():.1f}")
print("\nOOS R by entry setting (median over exits) for the 20 best IS entry settings:")
E = G.groupby(["rsi", "vol", "band"]).agg(IS=("IS_R", "median"), OOS=("OOS_R", "median"), n=("n", "median"))
print(E.sort_values("IS", ascending=False).head(20).round(1).to_string())
print(f"Spearman IS vs OOS across entry settings: {E.IS.rank().corr(E.OOS.rank()):.2f}")

# ---------------------------------------------------------------- C) random baseline for the claimed cell
print("\n== C) random entries, same count, same SL/TP ==")
rng = np.random.default_rng(7)
for lab, (T, sl, tp, side) in claimT.items():
    k = int((side != 0).sum())
    rnd = []
    for _ in range(300):
        rs_ = np.zeros_like(side)
        rs_[rng.choice(np.arange(1000, len(side)), size=k, replace=False)] = rng.choice([-1, 1], size=k)
        rnd.append(sim.run(B, rs_, c * sl / 100, c * tp / 100)["net"].sum() / sl)
    rnd = np.array(rnd)
    R = T["net"].sum() / sl
    print(f"{lab}: strategy {R:.1f}R | random median {np.median(rnd):.1f}R, 95th {np.percentile(rnd, 95):.1f}R "
          f"-> beats {(rnd < R).mean()*100:.0f}%")

# ---------------------------------------------------------------- D) other coins
print("\n== D) claimed cells on other coins ==")
for sym in ["DOGEUSDT", "SOLUSDT", "ETHUSDT", "BTCUSDT"]:
    s2, B2 = load(sym)
    c2 = B2["close"].to_numpy()
    for rs, vm, m, sl, tp, lab in CLAIMS:
        side = X.signals(B2, h=8.0, mult=m, rsi_os=rs, rsi_ob=100 - rs, vol_mult=vm)
        T = s2.run(B2, side, c2 * sl / 100, c2 * tp / 100)
        st = stats(T, sl)
        print(f"{sym} {lab[:22]:22s}: n {st['n']}, TP {st.get('TP')}, R {st.get('R', 0):.1f} "
              f"(IS {st.get('IS_R', 0):.1f} / OOS {st.get('OOS_R', 0):.1f})")
