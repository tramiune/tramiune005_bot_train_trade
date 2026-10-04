"""Can we give the DOGE 3m squeeze signal a DIRECTION edge? (TP = SL = 5%)
The squeeze signal says WHEN a big move is likely; here we test simple, pre-justified rules for WHICH WAY.
Step 1 (diagnostic): for every squeeze signal, the independent outcome "+5% or -5% first" (1m data).
         Each rule predicts up/down; we report its hit rate in-sample (<2025) and out-of-sample.
Step 2 (trading): one position at a time, TP 5% / SL 5%, taker + slippage + funding, for each rule
         (direction from the rule; 'agree' variants only trade when breakout direction agrees with it).
All features use data available at the signal bar close (higher timeframes only from CLOSED bars).
Usage (repo root): web_app/backend/.venv/bin/python .agents/skills/honest-backtest/scripts/squeeze_direction.py
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
SYMBOL = os.environ.get("SYMBOL", "DOGEUSDT")
TP = SL = 0.05

d1 = bt_data.load(SYMBOL, "1m")
sim = H.Sim(d1)
B = H.resample(d1, 3)
ct = B["close_time"].to_numpy()
c = B["close"].to_numpy()
brk = np.asarray(sig_squeeze(B, follow=True)); brk[:200] = 0   # +1 = breakout up, -1 = breakout down


def htf(minutes, fn):
    """Value of fn(higher-timeframe bars) from the last CLOSED HTF bar, aligned to 3m bars."""
    Hb = H.resample(d1, minutes)
    Hb["v"] = fn(Hb)
    m = pd.merge_asof(B[["close_time"]], Hb[["close_time", "v"]], on="close_time", direction="backward")
    return m["v"].to_numpy()


btc = bt_data.load("BTCUSDT", "1m")
Bb = H.resample(btc, 240); Bb["v"] = np.sign(Bb["close"] - H.ema(Bb["close"], 200))
btc_tr = pd.merge_asof(B[["close_time"]], Bb[["close_time", "v"]], on="close_time", direction="backward")["v"].to_numpy()

RULES = {
    "breakout (follow)": brk.astype(float),
    "4h EMA200 trend": np.sign(c - htf(240, lambda b: H.ema(b["close"], 200))),
    "4h EMA50 trend": np.sign(c - htf(240, lambda b: H.ema(b["close"], 50))),
    "1d EMA20 trend": np.sign(c - htf(1440, lambda b: H.ema(b["close"], 20))),
    "1h EMA200 trend": np.sign(c - htf(60, lambda b: H.ema(b["close"], 200))),
    "24h momentum": np.sign(c / pd.Series(c).shift(480).to_numpy() - 1),
    "7d momentum": np.sign(c / pd.Series(c).shift(3360).to_numpy() - 1),
    "4h Donchian100 position": np.sign(c - htf(240, lambda b: (b["high"].rolling(100).max() + b["low"].rolling(100).min()) / 2)),
    "BTC 4h EMA200 trend": btc_tr,
}

# ---- step 1: independent outcome of every squeeze signal
idx = np.nonzero(brk)[0]
up_first = np.full(len(idx), np.nan)
for n_, bi in enumerate(idx):
    j = int(np.searchsorted(sim.t, ct[bi]))
    if j >= sim.n:
        continue
    e = sim.o[j]
    k, is_sl = sim._first_hit(j, sim.n, 1, e * (1 - SL), e * (1 + TP))   # long view: TP=up 5%, SL=down 5%
    if k is not None:
        up_first[n_] = 0.0 if is_sl else 1.0
ok = ~np.isnan(up_first)
is_ = ct[idx] < H.SPLIT
print(f"{SYMBOL}: {len(idx)} squeeze signals | base rate '+5% first' IS {np.nanmean(up_first[is_])*100:.1f}% OOS {np.nanmean(up_first[~is_])*100:.1f}%")
print("\n== step 1: direction hit rate per rule (needs > ~51.4% to beat costs at 1:1) ==")
for name, d in RULES.items():
    p = d[idx]
    v = ok & (p != 0) & ~np.isnan(p)
    hit = (np.where(p > 0, up_first, 1 - up_first))
    print(f"{name:26s}: IS {np.nanmean(hit[v & is_])*100:5.1f}% (n {int((v & is_).sum())})  OOS {np.nanmean(hit[v & ~is_])*100:5.1f}% (n {int((v & ~is_).sum())})")

# ---- step 2: one-position-at-a-time trading with each rule
print("\n== step 2: trading TP 5% / SL 5%, one position at a time ==")
rows = []
for name, d in RULES.items():
    for mode in ("rule", "agree"):
        if name.startswith("breakout") and mode == "agree":
            continue
        side = np.where(brk != 0, np.sign(np.nan_to_num(d)), 0).astype(int)
        if mode == "agree":
            side = np.where(side == brk, side, 0)
        T = sim.run(B, side, c * SL, c * TP); H.check_trades(T)
        C = T[T.reason != "OPEN"]
        mi, mo = H.metrics(T, None, H.SPLIT), H.metrics(T, H.SPLIT)
        rows.append({"rule": name, "mode": mode, "n": len(C), "win%": (C.reason == "TP").mean() * 100,
                     "net_sum": C.net.sum(), "IS_n": mi.get("n", 0), "IS_win": mi.get("win%"), "IS_sum": mi.get("sum%"),
                     "OOS_n": mo.get("n", 0), "OOS_win": mo.get("win%"), "OOS_sum": mo.get("sum%")})
R = pd.DataFrame(rows)
print(R.round(1).to_string(index=False))
