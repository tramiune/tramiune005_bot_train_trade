"""Mean-reversion scalping research on DOGEUSDT USD-M futures (1m base data, local machine).

Families (all one position at a time, exits checked on 1m candles, IS < 2025-01-01 <= OOS):
  A_limit : resting LIMIT at the Bollinger band (maker), TP = middle band (maker limit), SL = m*ATR beyond
            the band, time-stop. Long at lower band / short at upper band. Optional 1h EMA200 trend filter.
  A_market: same idea with taker market entry after a close outside the band (comparison).
  B_rsi2  : RSI(2) extreme -> resting LIMIT p*ATR below/above close, TP = middle band, SL m*ATR.
Usage (repo root):
  web_app/backend/.venv/bin/python .agents/skills/honest-backtest/scripts/mr_search.py
"""
import itertools
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
import bt_data  # noqa: E402
import bt_harness as H  # noqa: E402

pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 40)
SYMBOL = os.environ.get("SYMBOL", "DOGEUSDT")
_G = {}


def build_tf(d1, minutes):
    B = H.resample(d1, minutes)
    c = B["close"]
    B["mid"] = c.rolling(20).mean()
    B["sd"] = c.rolling(20).std()
    B["atr"] = H.atr(B, 14)
    B["rsi2"] = H.rsi(c, 2)
    # 1h EMA200 trend, only from 1h bars already CLOSED at this bar's close
    h1 = H.resample(d1, 60)
    h1["ema200"] = H.ema(h1["close"], 200)
    m = pd.merge_asof(B[["close_time"]], h1[["close_time", "ema200"]], on="close_time", direction="backward")
    B["trend"] = np.sign(c.to_numpy() - m["ema200"].to_numpy())
    B.loc[m["ema200"].isna().to_numpy(), "trend"] = 0
    B.iloc[:250, B.columns.get_loc("trend")] = 0
    return B


def _init():
    d1 = bt_data.load(SYMBOL, "1m")
    _G["sim"] = H.Sim(d1)
    _G["tf"] = {m: build_tf(d1, m) for m in (5, 15)}


def run_one(cfg):
    fam, tf, k, m, trend, hold_bars, extra = cfg
    B, sim = _G["tf"][tf], _G["sim"]
    c, mid, sd, a = (B[x].to_numpy() for x in ("close", "mid", "sd", "atr"))
    lb, ub = mid - k * sd, mid + k * sd
    tr = B["trend"].to_numpy()
    n = len(B)
    hold = tf * hold_bars
    if fam == "A_limit":
        # side for the next bar: long order at lower band if close below mid, short at upper band otherwise
        side = np.where(c < mid, 1, -1)
        if trend:
            side = np.where(side == tr, side, 0)
        side[:250] = 0
        lim = np.where(side > 0, lb, ub)
        sl = np.where(side > 0, lb - m * a, ub + m * a)
        T = sim.run_limit(B, side, lim, mid, sl, valid_min=tf, max_hold_min=hold)
    elif fam == "A_market":
        side = np.where(c < lb, 1, np.where(c > ub, -1, 0))
        if trend:
            side = np.where(side == tr, side, 0)
        side[:250] = 0
        T = sim.run(B, side, m * a, np.abs(mid - c), max_hold_min=hold)
    else:  # B_rsi2
        th, p = extra
        r = B["rsi2"].to_numpy()
        side = np.where(r < th, 1, np.where(r > 100 - th, -1, 0))
        if trend:
            side = np.where(side == tr, side, 0)
        side[:250] = 0
        lim = c - side * p * a
        sl = lim - side * m * a
        T = sim.run_limit(B, side, lim, mid, sl, valid_min=tf * 3, max_hold_min=hold)
    H.check_trades(T)
    mi, mo = H.metrics(T, None, H.SPLIT), H.metrics(T, H.SPLIT)
    gi = T[T["entry_t"] < H.SPLIT]["gross"]; go = T[T["entry_t"] >= H.SPLIT]["gross"]
    row = {"IS_gross_ev": gi.mean(), "OOS_gross_ev": go.mean(), "fam": fam, "tf": f"{tf}m", "k": k, "m": m, "trend": trend, "hold_min": hold, "extra": str(extra),
           "unfilled": T.attrs.get("unfilled", 0)}
    for pre, mm in (("IS_", mi), ("OOS_", mo)):
        for key in ("n", "win%", "ev%", "sum%", "maxDD%", "PF", "hold_h"):
            row[pre + key.rstrip("%")] = mm.get(key, np.nan)
    return row


def configs():
    out = []
    for tf, k, m, trend, hb in itertools.product((5, 15), (2.0, 2.5, 3.0), (1.0, 1.5, 2.0), (False, True), (12, 48)):
        out.append(("A_limit", tf, k, m, trend, hb, None))
        out.append(("A_market", tf, k, m, trend, hb, None))
    for tf, th, p, m, trend, hb in itertools.product((5, 15), (5, 10), (0.0, 0.25, 0.5), (1.0, 1.5, 2.0), (False, True), (12, 48)):
        out.append(("B_rsi2", tf, 2.0, m, trend, hb, (th, p)))
    return out


if __name__ == "__main__":
    t0 = time.time()
    cf = configs()
    print(f"{SYMBOL}: {len(cf)} configurations, fees maker {H.FEE_MAKER}% / taker {H.FEE_SIDE}% + slip {H.SLIP_SIDE}%", flush=True)
    with ProcessPoolExecutor(max_workers=os.cpu_count(), initializer=_init) as ex:
        rows = list(ex.map(run_one, cf, chunksize=4))
    R = pd.DataFrame(rows)
    out_csv = os.path.join(bt_data.ROOT, f"mr_search_{SYMBOL}.csv")
    R.to_csv(out_csv, index=False)
    print(f"done in {time.time()-t0:.0f}s -> {out_csv}")

    print("\n== BEFORE costs (gross EV % per trade): does any edge exist at all? ==")
    print(R.groupby(["fam", "tf"]).agg(pos_gross_IS=("IS_gross_ev", lambda s: (s > 0).mean() * 100),
                                       pos_gross_OOS=("OOS_gross_ev", lambda s: (s > 0).mean() * 100),
                                       med_gross_IS=("IS_gross_ev", "median"), med_gross_OOS=("OOS_gross_ev", "median"),
                                       best_gross_OOS=("OOS_gross_ev", "max")).round(4).to_string())
    print(f"\nIS profitable: {(R.IS_ev > 0).sum()} | OOS profitable: {(R.OOS_ev > 0).sum()} | both: {((R.IS_ev > 0) & (R.OOS_ev > 0)).sum()} of {len(R)}")
    print("\n== per family: share of configs with positive EV, median win% and EV (net % per trade) ==")
    g = R.groupby(["fam", "tf"]).agg(n=("IS_n", "size"), pos_IS=("IS_ev", lambda s: (s > 0).mean() * 100),
                                      pos_OOS=("OOS_ev", lambda s: (s > 0).mean() * 100),
                                      med_IS_win=("IS_win", "median"), med_IS_ev=("IS_ev", "median"),
                                      med_OOS_win=("OOS_win", "median"), med_OOS_ev=("OOS_ev", "median"),
                                      med_trades_IS=("IS_n", "median"))
    print(g.round(3).to_string())
    cand = R[(R["IS_n"] >= 200) & (R["IS_ev"] > 0)].sort_values("IS_PF", ascending=False)
    cols = ["fam", "tf", "k", "m", "trend", "hold_min", "extra", "IS_n", "IS_win", "IS_ev", "IS_sum", "IS_maxDD", "IS_PF",
            "OOS_n", "OOS_win", "OOS_ev", "OOS_sum", "OOS_maxDD", "OOS_PF", "unfilled"]
    print(f"\n== chosen on IN-SAMPLE only (IS_n>=200, IS_ev>0, by IS PF): {len(cand)} candidates; top 15 ==")
    print(cand[cols].head(15).round(3).to_string(index=False))
    print("\n== highest IN-SAMPLE win rate (IS_n>=200) and what happened out-of-sample ==")
    print(R[R["IS_n"] >= 200].sort_values("IS_win", ascending=False)[cols].head(10).round(3).to_string(index=False))
