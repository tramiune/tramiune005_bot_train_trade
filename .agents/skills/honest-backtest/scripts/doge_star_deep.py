"""Deep dive: 4h Morning/Evening Star after a prior counter-move, on DOGEUSDT futures.
Default parameters are exactly those of candle_clusters.py (body of middle candle < 30% of candle 1,
candle 1 body > 20-bar average body, candle 3 closes beyond the midpoint of candle 1 body,
close 10 bars before the pattern on the other side of candle 1 open). Nothing re-tuned for the headline.
Checks: per year, long/short, random baseline, bootstrap CI, parameter neighbourhood (IS-ranked),
streaks and drawdown with 1% risk per trade, combination with 4h Donchian100.
Usage (repo root): web_app/backend/.venv/bin/python .agents/skills/honest-backtest/scripts/doge_star_deep.py
"""
import itertools
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
import bt_data  # noqa: E402
import bt_harness as H  # noqa: E402
from strategy_signals import sig_donchian  # noqa: E402

pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 30)
SYMBOL = os.environ.get("SYMBOL", "DOGEUSDT")
rng_ = np.random.default_rng(3)


def star(B, small=0.3, look=10, pen=0.5):
    o, h, l, c = (B[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)

    def sh(a, k):
        out = np.full(n, np.nan); out[k:] = a[:n - k]; return out
    o2, c2, o1, c1, o0, c0 = sh(o, 2), sh(c, 2), sh(o, 1), sh(c, 1), o, c
    b2, b1 = np.abs(c2 - o2), np.abs(c1 - o1)
    avg = pd.Series(np.abs(c - o)).rolling(20).mean().shift(3).to_numpy()
    base = (b2 > avg) & (b1 < small * b2)
    mstar = base & (c2 < o2) & (c0 > o0) & (c0 > c2 + pen * (o2 - c2))
    estar = base & (c2 > o2) & (c0 < o0) & (c0 < c2 - pen * (c2 - o2))
    before = sh(c, 2 + look)
    side = np.where(mstar & (before > o2), 1, np.where(estar & (before < o2), -1, 0))
    lo = np.fmin(np.fmin(sh(l, 2), sh(l, 1)), l)
    hi = np.fmax(np.fmax(sh(h, 2), sh(h, 1)), h)
    risk = np.where(side > 0, c - lo, hi - c)
    side = np.where(risk >= c * 0.002, side, 0)
    side[:40] = 0
    return side, risk


def with_r(T, B, risk):
    """Add R multiple (net % / initial risk %) using the signal bar's risk."""
    ct = B["close_time"].to_numpy()
    rk = dict(zip(ct, risk))
    rp = np.array([rk[t] for t in T["entry_t"]]) / T["entry"].to_numpy() * 100
    T = T.copy(); T["risk%"] = rp; T["R"] = T["net"] / rp
    return T


def risk_sim(R, risk_pct=1.0):
    eq = np.cumprod(1 + R * risk_pct / 100)
    dd = (1 - eq / np.maximum.accumulate(eq)).max() * 100
    streak = cur = 0
    for x in R:
        cur = cur + 1 if x <= 0 else 0; streak = max(streak, cur)
    return (eq[-1] - 1) * 100, dd, streak


d1 = bt_data.load(SYMBOL, "1m")
sim = H.Sim(d1)
B = H.resample(d1, 240)
c = B["close"].to_numpy()
side, risk = star(B)
print(f"{SYMBOL} 4h star+trend: {int((side != 0).sum())} signals ({int((side > 0).sum())} long / {int((side < 0).sum())} short)")

print("\n== 1) headline (default params) ==")
res = {}
for rr in (1.0, 1.5, 2.0):
    T = with_r(sim.run(B, side, risk, risk * rr), B, risk); H.check_trades(T); res[rr] = T
    m, mi, mo = H.metrics(T), H.metrics(T, None, H.SPLIT), H.metrics(T, H.SPLIT)
    boot = np.array([rng_.choice(T.R.to_numpy(), len(T)).mean() for _ in range(5000)])
    ret1, dd1, st = risk_sim(T.R.to_numpy(), 1.0)
    print(f"RR {rr}: n {m['n']} win {m['win%']:.1f}% (BE {100/(1+rr):.0f}%) | avg R {T.R.mean():+.3f} "
          f"[90% CI {np.percentile(boot,5):+.3f}, {np.percentile(boot,95):+.3f}] | IS {mi['n']} tr {mi['win%']:.1f}% win {T[T.entry_t<H.SPLIT].R.sum():+.1f}R "
          f"| OOS {mo['n']} tr {mo['win%']:.1f}% win {T[T.entry_t>=H.SPLIT].R.sum():+.1f}R | 1% risk/trade: {ret1:+.0f}%, maxDD {dd1:.0f}%, "
          f"longest losing streak {st} | median risk {T['risk%'].median():.2f}% | hold {T.hold_h.median():.0f}h")

print("\n== 2) per year (R) and long vs short, RR 1 and 1.5 ==")
for rr in (1.0, 1.5):
    T = res[rr]
    y = pd.to_datetime(T.entry_t, unit="s").dt.year
    print(f"RR {rr} per year:", T.groupby(y).agg(n=("R", "size"), win=("R", lambda s: round((s > 0).mean() * 100)),
                                                 R=("R", lambda s: round(s.sum(), 1))).to_dict("index"))
    for sd, nm in ((1, "LONG"), (-1, "SHORT")):
        S = T[T.side == sd]
        print(f"   {nm}: n {len(S)} win {(S.R > 0).mean()*100:.1f}% sum {S.R.sum():+.1f}R")

print("\n== 3) random baseline: random bars, random side, SL at the 3-bar extreme, same RR ==")
lo3 = np.fmin.reduce([np.roll(B.low.to_numpy(), k) for k in range(3)])
hi3 = np.fmax.reduce([np.roll(B.high.to_numpy(), k) for k in range(3)])
k = int((side != 0).sum())
for rr in (1.0, 1.5):
    sums = []
    for _ in range(300):
        rs = np.zeros(len(B), dtype=int)
        rs[rng_.choice(np.arange(40, len(B)), size=k, replace=False)] = rng_.choice([-1, 1], size=k)
        rk = np.where(rs > 0, c - lo3, hi3 - c)
        rs = np.where(rk >= c * 0.002, rs, 0)
        Tr = with_r(sim.run(B, rs, rk, rk * rr), B, rk)
        sums.append(Tr.R.mean())
    sums = np.array(sums)
    print(f"RR {rr}: random avg R median {np.median(sums):+.3f}, 95th pct {np.percentile(sums,95):+.3f} | "
          f"strategy {res[rr].R.mean():+.3f} beats {(sums < res[rr].R.mean()).mean()*100:.0f}% of random runs")

print("\n== 4) parameter neighbourhood (RR 1), ranked by IN-SAMPLE R ==")
rows = []
for small, look, pen in itertools.product((0.2, 0.3, 0.4, 0.5), (5, 10, 20), (0.5, 0.65)):
    s2, r2 = star(B, small, look, pen)
    T = with_r(sim.run(B, s2, r2, r2), B, r2)
    rows.append({"small": small, "look": look, "pen": pen, "n": len(T), "win%": (T.R > 0).mean() * 100,
                 "IS_R": T[T.entry_t < H.SPLIT].R.sum(), "OOS_R": T[T.entry_t >= H.SPLIT].R.sum(),
                 "default": (small, look, pen) == (0.3, 10, 0.5)})
P = pd.DataFrame(rows).sort_values("IS_R", ascending=False)
print(P.round(1).to_string(index=False))
print(f"positive IS: {(P.IS_R>0).sum()}/{len(P)} | positive OOS: {(P.OOS_R>0).sum()}/{len(P)} | both: {((P.IS_R>0)&(P.OOS_R>0)).sum()}")

print("\n== 5) combine with 4h Donchian100 (SL 1.5 ATR, TP 3 ATR), separate positions, 1% risk each ==")
A = H.atr(B, 14).to_numpy()
sg = np.asarray(sig_donchian(B, 100)); sg[:210] = 0
Td = with_r(sim.run(B, sg, A * 1.5, A * 3.0), B, A * 1.5)
Ts = res[1.0]
for name, T in (("star RR1", Ts), ("donchian100", Td), ("both", pd.concat([Ts, Td]).sort_values("exit_t"))):
    ret1, dd1, st = risk_sim(T.R.to_numpy(), 1.0)
    y = pd.to_datetime(T.entry_t, unit="s").dt.year
    print(f"{name:12s}: n {len(T)} win {(T.R>0).mean()*100:.1f}% sum {T.R.sum():+.1f}R | 1% risk: {ret1:+.0f}% maxDD {dd1:.0f}% "
          f"streak {st} | per year R {T.groupby(y).R.sum().round(1).to_dict()}")
mo = lambda T: T.groupby(pd.to_datetime(T.exit_t, unit='s').dt.to_period('M')).R.sum()
j = pd.concat([mo(Ts), mo(Td)], axis=1).fillna(0)
print(f"monthly R correlation star vs donchian: {j.corr().iloc[0,1]:+.2f}")
