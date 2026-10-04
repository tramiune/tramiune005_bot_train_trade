"""Nadaraya-Watson SCALPING on 5m (non-repainting NW endpoint estimator, h=8, 500 bars), 5 coins.
Strictly ONE position at a time per coin; signals while a trade is open are ignored.
Families:
  A_reentry : previous 5m close OUTSIDE the band, current close back INSIDE -> trade back toward the NW line
  A_rsi     : same, plus RSI(14) < 30 (long) / > 70 (short) on the previous bar
  B_slope   : NW line turns (slope flips) -> trade in the new direction
Exits (time-stop 2h = 24 bars for every scalp):
  A_*: TP = NW line at signal ("mid"), or TP = 1R / 1.5R; SL = extreme of the last 3 bars
  B  : SL / TP in ATR(14) multiples
Costs: taker 0.05% + slippage 0.02% each side + funding. Entry next bar open, exits on 1m, SL first.
IS < 2025-01-01 <= OOS. Usage (repo root):
  web_app/backend/.venv/bin/python .agents/skills/honest-backtest/scripts/nada_scalp.py
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
COINS = ["DOGEUSDT", "XRPUSDT", "SOLUSDT", "ETHUSDT", "BTCUSDT"]
HOLD_MIN = 120


def nw_env(c, h=8.0):
    w = np.exp(-(np.arange(500) ** 2) / (h * h * 2))
    out = np.convolve(c, w)[: len(c)] / w.sum()
    out[:499] = np.nan
    mae = pd.Series(np.abs(c - out)).rolling(499).mean().to_numpy()
    return out, mae


def build(B):
    c, l, h = (B[k].to_numpy() for k in ("close", "low", "high"))
    out, mae = nw_env(c)
    r = X.pine_rsi(c, 14)
    lo3 = pd.Series(l).rolling(3).min().to_numpy()
    hi3 = pd.Series(h).rolling(3).max().to_numpy()
    atr = H.atr(B, 14).to_numpy()
    return dict(c=c, out=out, mae=mae, rsi=r, lo3=lo3, hi3=hi3, atr=atr)


def configs():
    cf = []
    for fam, mult, ex in itertools.product(("A_reentry", "A_rsi"), (2.0, 2.5, 3.0), ("mid", 1.0, 1.5)):
        cf.append((fam, mult, ex))
    for ex in ((1.0, 1.5), (1.0, 2.0), (1.5, 1.5)):
        cf.append(("B_slope", 0.0, ex))  # mult unused for B
    return cf


def run(sim, B, D, fam, mult, ex):
    c, out = D["c"], D["out"]
    pc = np.roll(c, 1)
    if fam.startswith("A"):
        up, lo = out + mult * D["mae"], out - mult * D["mae"]
        pup, plo = np.roll(up, 1), np.roll(lo, 1)
        L = (pc < plo) & (c > lo)
        S = (pc > pup) & (c < up)
        if fam == "A_rsi":
            pr = np.roll(D["rsi"], 1)
            L, S = L & (pr < 30), S & (pr > 70)
        side = np.where(L, 1, np.where(S, -1, 0))
        risk = np.where(side > 0, c - D["lo3"], D["hi3"] - c)
        if ex == "mid":
            tpd = np.where(side > 0, out - c, c - out)
        else:
            tpd = risk * ex
        ok = (risk >= c * 0.0015) & (tpd >= c * 0.0015)
    else:
        sl1 = np.sign(out - np.roll(out, 1)); sl0 = np.roll(sl1, 1)
        side = np.where((sl1 > 0) & (sl0 <= 0), 1, np.where((sl1 < 0) & (sl0 >= 0), -1, 0))
        risk, tpd = D["atr"] * ex[0], D["atr"] * ex[1]
        ok = risk >= c * 0.0015
    side = np.where(ok, side, 0)
    side[:1000] = 0
    T = sim.run(B, side, risk, tpd, max_hold_min=HOLD_MIN)
    H.check_trades(T)
    return T


if __name__ == "__main__":
    rows, store = [], {}
    for sym in COINS:
        d1 = bt_data.load(sym, "1m")
        sim = H.Sim(d1)
        B = H.resample(d1, 5)
        D = build(B)
        for fam, mult, ex in configs():
            T = run(sim, B, D, fam, mult, ex)
            store[(sym, fam, mult, str(ex))] = T
            rows.append({"coin": sym, "fam": fam, "mult": mult, "exit": str(ex), "n": len(T),
                         "win%": (T.net > 0).mean() * 100 if len(T) else np.nan,
                         "gross_ev": T.gross.mean() if len(T) else np.nan, "net_ev": T.net.mean() if len(T) else np.nan,
                         "IS": T.loc[T.entry_t < H.SPLIT, "net"].sum(), "OOS": T.loc[T.entry_t >= H.SPLIT, "net"].sum(),
                         "hold_min": T.hold_h.mean() * 60 if len(T) else np.nan,
                         "time_exits%": (T.reason == "TIME").mean() * 100 if len(T) else np.nan})
        print(f"done {sym}", flush=True)
    R = pd.DataFrame(rows)
    R.to_csv(os.path.join(bt_data.ROOT, "nada_scalp.csv"), index=False)
    print("\n== POOLED 5 coins (one position at a time per coin) ==")
    for (fam, mult, ex), g in R.groupby(["fam", "mult", "exit"], dropna=False, sort=False):
        P = pd.concat([store[(s, fam, mult, ex)] for s in COINS])
        r = P["net"].to_numpy()
        print(f"{fam:10s} mult {str(mult):4s} exit {ex:10s}: trades {len(P):6d} ({len(P)/5/49:5.1f}/coin/mo) win {(r>0).mean()*100:5.1f}% "
              f"gross {P.gross.mean():+.3f}% net {r.mean():+.3f}% | IS {P.loc[P.entry_t<H.SPLIT,'net'].sum():+7.0f}% "
              f"OOS {P.loc[P.entry_t>=H.SPLIT,'net'].sum():+7.0f}% | coins+ {int((g.IS+g.OOS>0).sum())}/5 | hold {P.hold_h.mean()*60:.0f}m")
    best = R[(R.IS > 0)].sort_values("IS", ascending=False)
    print(f"\ncoin-level configs positive IS: {(R.IS>0).sum()} | OOS: {(R.OOS>0).sum()} | both: {((R.IS>0)&(R.OOS>0)).sum()} of {len(R)}")
    print(best.head(12).round(3).to_string(index=False))
