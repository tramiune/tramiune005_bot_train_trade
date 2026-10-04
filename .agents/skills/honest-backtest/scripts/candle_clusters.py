"""Multi-candle patterns from Bulkowski's top rankings, tested on 5 coins (1h / 4h / 1d).

Patterns (no gap requirement: crypto trades 24/7):
  three_line_strike : 3 falling black candles, 4th white opens <= 3rd close and closes > 1st open  -> LONG
                      (Bulkowski: acts as bullish reversal 84%); mirror -> SHORT
  crows_soldiers    : three black crows (3 long black candles, each opens inside prior body, closes
                      lower, close in lower 25% of range) -> SHORT; three white soldiers mirror -> LONG
  star              : morning star (long black, small body < 30% of it, white closing above the midpoint
                      of candle 1 body) -> LONG; evening star mirror -> SHORT
  each also "+trend": the move before the pattern goes the other way (close 10 bars before pattern
                      start is above/below), i.e. a real reversal context; candles only, no indicator.
Measured:
  breakout%: which pattern boundary is touched first after completion (Bulkowski-style "success")
  trades   : entry next bar open, SL = pattern extreme, TP = RR x risk, RR 1 / 1.5 / 2,
             exits on 1m, SL first, taker + slippage + funding, one position at a time per coin.
Usage (repo root): web_app/backend/.venv/bin/python .agents/skills/honest-backtest/scripts/candle_clusters.py
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
import bt_data  # noqa: E402
import bt_harness as H  # noqa: E402

pd.set_option("display.width", 250)
COINS = ["DOGEUSDT", "XRPUSDT", "SOLUSDT", "ETHUSDT", "BTCUSDT"]
TFS = {"1h": 60, "4h": 240, "1d": 1440}
RRS = [1.0, 1.5, 2.0]


def sh(a, k):
    out = np.roll(a, k).astype(float)
    out[:k] = np.nan
    return out


def find(B):
    o, h, l, c = (B[k].to_numpy() for k in ("open", "high", "low", "close"))
    O = {k: sh(o, k) for k in range(4)}; Cc = {k: sh(c, k) for k in range(4)}
    Hh = {k: sh(h, k) for k in range(4)}; Ll = {k: sh(l, k) for k in range(4)}
    black = {k: Cc[k] < O[k] for k in range(4)}; white = {k: Cc[k] > O[k] for k in range(4)}
    body = {k: np.abs(Cc[k] - O[k]) for k in range(4)}; rng = {k: Hh[k] - Ll[k] for k in range(4)}
    res = {}
    # three line strike (bars 3,2,1 then strike bar 0)
    bear3 = black[3] & black[2] & black[1] & (Cc[2] < Cc[3]) & (Cc[1] < Cc[2])
    bull3 = white[3] & white[2] & white[1] & (Cc[2] > Cc[3]) & (Cc[1] > Cc[2])
    long_ = bear3 & white[0] & (O[0] <= Cc[1]) & (Cc[0] > O[3])
    short = bull3 & black[0] & (O[0] >= Cc[1]) & (Cc[0] < O[3])
    lo = np.fmin.reduce([Ll[k] for k in range(4)]); hi = np.fmax.reduce([Hh[k] for k in range(4)])
    res["three_line_strike"] = (np.where(long_, 1, np.where(short, -1, 0)), lo, hi, 4)
    # three black crows / white soldiers (bars 2,1,0)
    avg_body = pd.Series(np.abs(c - o)).rolling(20).mean().shift(3).to_numpy()
    longb = {k: body[k] > avg_body for k in range(3)}
    crows = (black[2] & black[1] & black[0] & longb[2] & longb[1] & longb[0]
             & (O[1] <= O[2]) & (O[1] >= Cc[2]) & (O[0] <= O[1]) & (O[0] >= Cc[1])
             & (Cc[1] < Cc[2]) & (Cc[0] < Cc[1])
             & ((Cc[0] - Ll[0]) <= 0.25 * rng[0]) & ((Cc[1] - Ll[1]) <= 0.25 * rng[1]))
    soldiers = (white[2] & white[1] & white[0] & longb[2] & longb[1] & longb[0]
                & (O[1] >= O[2]) & (O[1] <= Cc[2]) & (O[0] >= O[1]) & (O[0] <= Cc[1])
                & (Cc[1] > Cc[2]) & (Cc[0] > Cc[1])
                & ((Hh[0] - Cc[0]) <= 0.25 * rng[0]) & ((Hh[1] - Cc[1]) <= 0.25 * rng[1]))
    lo3 = np.fmin.reduce([Ll[k] for k in range(3)]); hi3 = np.fmax.reduce([Hh[k] for k in range(3)])
    res["crows_soldiers"] = (np.where(soldiers, 1, np.where(crows, -1, 0)), lo3, hi3, 3)
    # morning / evening star (bars 2,1,0)
    mstar = black[2] & longb[2] & (body[1] < 0.3 * body[2]) & white[0] & (Cc[0] > (O[2] + Cc[2]) / 2)
    estar = white[2] & longb[2] & (body[1] < 0.3 * body[2]) & black[0] & (Cc[0] < (O[2] + Cc[2]) / 2)
    res["star"] = (np.where(mstar, 1, np.where(estar, -1, 0)), lo3, hi3, 3)
    # + trend context (reversal patterns need a prior move the other way; soldiers/crows: prior opposite move)
    for name in list(res):
        s, lo_, hi_, nb = res[name]
        start_close = sh(c, nb - 1)          # close of first pattern bar... use open of it instead:
        start_open = sh(o, nb - 1)
        before = sh(c, nb - 1 + 10)
        prior_down = before > start_open
        prior_up = before < start_open
        s2 = np.where((s > 0) & prior_down, 1, np.where((s < 0) & prior_up, -1, 0))
        res[name + "+trend"] = (s2, lo_, hi_, nb)
    for v in res.values():
        v[0][:40] = 0
    return res


def breakout_first(sim, B, side, lo, hi):
    """Bulkowski-style: after the pattern closes, which boundary is touched first (on 1m)?"""
    ct = B["close_time"].to_numpy()
    up = dn = 0
    for bi in np.nonzero(side)[0]:
        j = int(np.searchsorted(sim.t, ct[bi]))
        if j >= sim.n:
            continue
        hit_hi = np.nonzero(sim.h[j:] > hi[bi])[0]
        hit_lo = np.nonzero(sim.l[j:] < lo[bi])[0]
        a = hit_hi[0] if len(hit_hi) else np.inf
        b = hit_lo[0] if len(hit_lo) else np.inf
        if a == b == np.inf:
            continue
        if a < b:
            up += side[bi] > 0
            dn += side[bi] < 0
        elif b < a:
            up += side[bi] < 0  # for shorts, "success" = breaks the low first
            dn += side[bi] > 0
    tot = up + dn
    return (up / tot * 100 if tot else np.nan), tot


rows, store = [], {}
for sym in COINS:
    d1 = bt_data.load(sym, "1m")
    sim = H.Sim(d1)
    for tfn, mins in TFS.items():
        B = H.resample(d1, mins)
        c = B["close"].to_numpy()
        for pname, (side, lo, hi, nb) in find(B).items():
            risk = np.where(side > 0, c - lo, hi - c)
            side = np.where(risk >= c * 0.002, side, 0)
            succ, nsig = breakout_first(sim, B, side, lo, hi)
            for rr in RRS:
                T = sim.run(B, side, risk, risk * rr)
                H.check_trades(T)
                store[(sym, tfn, pname, rr)] = T
                rows.append({"coin": sym, "tf": tfn, "pattern": pname, "rr": rr, "signals": nsig,
                             "breakout_ok%": succ, "n": len(T), "sum%": T.net.sum()})
R = pd.DataFrame(rows)
R.to_csv(os.path.join(bt_data.ROOT, "candle_clusters.csv"), index=False)
print("== POOLED 5 coins ==  breakout_ok% = pattern boundary in the predicted direction touched first (Bulkowski-style)")
for (tfn, pname), g in R.groupby(["tf", "pattern"], sort=False):
    g1 = g[g.rr == 1.0]
    sig = int(g1.signals.sum())
    bo = np.nansum(g1["breakout_ok%"] * g1.signals) / sig if sig else np.nan
    line = f"{tfn:3s} {pname:24s} signals {sig:5d}  breakout_ok {bo:5.1f}% |"
    for rr in RRS:
        P = pd.concat([store[(s, tfn, pname, rr)] for s in COINS])
        r = P["net"].to_numpy()
        if len(r):
            line += (f" RR{rr:g}: n {len(r):4d} win {(r>0).mean()*100:4.1f}% (BE {100/(1+rr):.0f}%) "
                     f"EV {r.mean():+.2f}% IS {P.loc[P.entry_t<H.SPLIT,'net'].sum():+5.0f} OOS {P.loc[P.entry_t>=H.SPLIT,'net'].sum():+5.0f} |")
    print(line)
print(f"\ncoin-level cells with win >= 70% at RR >= 1 and n >= 20: "
      f"{sum(((store[k]['net'] > 0).mean() >= 0.7) and len(store[k]) >= 20 for k in store)} of {len(store)}")
