"""Pure price-action (candles only, no indicators) test on 5 coins, 1h and 4h.
Patterns: engulfing, pin bar (hammer / shooting star), inside-bar breakout; each also in a variant that
requires the pattern to sit at a 20-bar extreme (price structure, still no indicator).
SL = pattern extreme (structure), TP = RR x risk. Honest rules: next-bar-open entry, exits on 1m,
SL first, taker + slippage + funding, one position at a time per coin. IS < 2025-01-01 <= OOS.
Usage (repo root): web_app/backend/.venv/bin/python .agents/skills/honest-backtest/scripts/price_action.py
"""
import itertools
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
import bt_data  # noqa: E402
import bt_harness as H  # noqa: E402

pd.set_option("display.width", 250)
COINS = ["DOGEUSDT", "XRPUSDT", "SOLUSDT", "ETHUSDT", "BTCUSDT"]
TFS = {"1h": 60, "4h": 240}
RRS = [0.5, 1.0, 1.5, 2.0]


def patterns(B):
    o, h, l, c = (B[k].to_numpy() for k in ("open", "high", "low", "close"))
    po, pc, ph, pl = np.roll(o, 1), np.roll(c, 1), np.roll(h, 1), np.roll(l, 1)
    rng = h - l
    body = np.abs(c - o)
    up_w = h - np.maximum(o, c)
    dn_w = np.minimum(o, c) - l
    out = {}
    # engulfing (body engulfs previous body, opposite colour)
    bull = (pc < po) & (c > o) & (c >= po) & (o <= pc)
    bear = (pc > po) & (c < o) & (c <= po) & (o >= pc)
    out["engulfing"] = (np.where(bull, 1, np.where(bear, -1, 0)), np.minimum(l, pl), np.maximum(h, ph))
    # pin bar: long wick >= 2x body and >= 60% of range, close in the outer third
    hammer = (dn_w >= 2 * body) & (dn_w >= 0.6 * rng) & (c >= l + 2 / 3 * rng)
    star = (up_w >= 2 * body) & (up_w >= 0.6 * rng) & (c <= l + 1 / 3 * rng)
    out["pinbar"] = (np.where(hammer, 1, np.where(star, -1, 0)), l, h)
    # inside bar breakout: bar i-1 inside bar i-2, bar i closes beyond the mother bar
    mh, ml = np.roll(h, 2), np.roll(l, 2)
    inside = (ph <= mh) & (pl >= ml)
    out["insidebar"] = (np.where(inside & (c > mh), 1, np.where(inside & (c < ml), -1, 0)), np.roll(l, 1), np.roll(h, 1))
    # variants at a 20-bar extreme (pattern low is the lowest low of the last 20 bars, or highest high)
    ll20 = pd.Series(l).rolling(20).min().to_numpy()
    hh20 = pd.Series(h).rolling(20).max().to_numpy()
    for name in list(out):
        s, lo, hi = out[name]
        s2 = np.where((s > 0) & (lo <= ll20), 1, np.where((s < 0) & (hi >= hh20), -1, 0))
        out[name + "@extreme"] = (s2, lo, hi)
    for name in out:
        out[name][0][:25] = 0
    return out


rows, store = [], {}
for sym in COINS:
    d1 = bt_data.load(sym, "1m")
    sim = H.Sim(d1)
    for tfn, mins in TFS.items():
        B = H.resample(d1, mins)
        c = B["close"].to_numpy()
        for pname, (side, lo, hi) in patterns(B).items():
            risk = np.where(side > 0, c - lo, hi - c)
            ok = risk >= c * 0.002           # skip patterns with < 0.2% risk (fees would dominate)
            side = np.where(ok, side, 0)
            for rr in RRS:
                T = sim.run(B, side, risk, risk * rr)
                H.check_trades(T)
                store[(sym, tfn, pname, rr)] = T
                rows.append({"coin": sym, "tf": tfn, "pattern": pname, "rr": rr, "n": len(T),
                             "win%": (T.net > 0).mean() * 100 if len(T) else np.nan,
                             "sum%": T.net.sum(), "IS": T.loc[T.entry_t < H.SPLIT, "net"].sum(),
                             "OOS": T.loc[T.entry_t >= H.SPLIT, "net"].sum()})
R = pd.DataFrame(rows)
R.to_csv(os.path.join(bt_data.ROOT, "price_action.csv"), index=False)
cost = 2 * (H.FEE_SIDE + H.SLIP_SIDE)
print("== POOLED over 5 coins: win rate vs break-even (break-even = 1/(1+RR), before costs) ==")
for (tfn, pname, rr), g in R.groupby(["tf", "pattern", "rr"]):
    P = pd.concat([store[(s, tfn, pname, rr)] for s in COINS])
    r = P["net"].to_numpy()
    print(f"{tfn:3s} {pname:20s} RR {rr:<3}: trades {len(P):5d} ({len(P)/5/49:.1f}/coin/mo) win {(r>0).mean()*100:5.1f}% "
          f"(BE {100/(1+rr):4.1f}%) EV {r.mean():+.3f}%  IS {P.loc[P.entry_t<H.SPLIT,'net'].sum():+7.0f}%  "
          f"OOS {P.loc[P.entry_t>=H.SPLIT,'net'].sum():+7.0f}%  coins+ {int((g['sum%']>0).sum())}/5")
print(f"\ncombos tested: {len(R)} | coin-level combos with win >= 70% and RR >= 1: "
      f"{int(((R['win%'] >= 70) & (R.rr >= 1) & (R.n >= 30)).sum())}")
