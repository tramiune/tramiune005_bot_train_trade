"""Learning filters from LOSING trades, done honestly (walk-forward) vs the usual way (in-sample).

Base signal: NW 5m scalp A_rsi (mult 2.5, TP = NW line, SL = 3-bar extreme, 2h time-stop), 5 coins.
Features known at the signal bar close: hour (UTC), weekday, RSI, distance to NW line in ATR, band width,
volume ratio, 1h-EMA200 trend agreement, 1h momentum in trade direction, ATR%.
Filter model: for every feature, bin it (quantiles fitted on the training trades) and score each bin by
its average net result minus the overall average; a signal's score = sum of its bin scores; only signals
whose score is in the top X% of the TRAINING scores are traded.
  - IN-SAMPLE ("cheating"): learn on all signals, apply to the same signals.
  - WALK-FORWARD (honest): every quarter from 2024-01, learn only from signals whose trade had already
    finished before the quarter starts, apply to that quarter's signals; then simulate ONE position at a
    time on the filtered signals.
Usage (repo root): web_app/backend/.venv/bin/python .agents/skills/honest-backtest/scripts/loss_filter_wf.py
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
import bt_data  # noqa: E402
import bt_harness as H  # noqa: E402
import nada_scalp as NS  # noqa: E402

pd.set_option("display.width", 250)
COINS = ["DOGEUSDT", "XRPUSDT", "SOLUSDT", "ETHUSDT", "BTCUSDT"]
MULT, HOLD = 2.5, NS.HOLD_MIN
WF_START = pd.Timestamp("2024-01-01", tz="UTC")
TOPS = (0.3, 0.2, 0.1)
CAT = {"hour4", "dow", "trend_agree"}


def signal_arrays(B, D):
    c, out = D["c"], D["out"]
    up, lo = out + MULT * D["mae"], out - MULT * D["mae"]
    pc, pup, plo, pr = np.roll(c, 1), np.roll(up, 1), np.roll(lo, 1), np.roll(D["rsi"], 1)
    L = (pc < plo) & (c > lo) & (pr < 30)
    S = (pc > pup) & (c < up) & (pr > 70)
    side = np.where(L, 1, np.where(S, -1, 0))
    risk = np.where(side > 0, c - D["lo3"], D["hi3"] - c)
    tpd = np.where(side > 0, out - c, c - out)
    ok = (risk >= c * 0.0015) & (tpd >= c * 0.0015)
    side = np.where(ok, side, 0); side[:1000] = 0
    return side, risk, tpd


def features(B, D, d1):
    c = D["c"]; v = B["volume"].to_numpy()
    h1 = H.resample(d1, 60); h1["ema"] = H.ema(h1["close"], 200)
    m = pd.merge_asof(B[["close_time"]], h1[["close_time", "ema"]], on="close_time", direction="backward")
    ct = B["close_time"].to_numpy()
    return pd.DataFrame({
        "hour4": (ct // 3600 % 24) // 4, "dow": pd.to_datetime(ct, unit="s").dayofweek,
        "rsi": np.roll(D["rsi"], 1), "dist_atr": np.abs(c - D["out"]) / D["atr"], "bw": D["mae"] / c,
        "volr": v / pd.Series(v).rolling(20).mean().to_numpy(),
        "trend": np.sign(c - m["ema"].to_numpy()), "mom12": c / np.roll(c, 12) - 1, "atrp": D["atr"] / c})


def outcomes(sim, B, side, risk, tpd):
    """Independent outcome of EVERY signal (used only as training labels once the trade has finished)."""
    ct = B["close_time"].to_numpy(); max_c = HOLD
    rows = []
    for bi in np.nonzero(side)[0]:
        j = int(np.searchsorted(sim.t, ct[bi]))
        if j >= sim.n or sim.t[j] != ct[bi]:
            continue
        s, e = int(side[bi]), sim.o[j]
        sl, tp = e - s * risk[bi], e + s * tpd[bi]
        end = min(sim.n, j + max_c)
        k, is_sl = sim._first_hit(j, end, s, sl, tp)
        if k is None:
            k, x = end - 1, sim.c[end - 1]
        elif is_sl:
            gap = (sim.o[k] <= sl) if s > 0 else (sim.o[k] >= sl)
            x = sim.o[k] if (gap and k > j) else sl
        else:
            x = tp
        hold_h = (sim.t[k] + 60 - sim.t[j]) / 3600
        net = s * (x / e - 1) * 100 - 2 * (H.FEE_SIDE + H.SLIP_SIDE) - H.FUNDING_PER_8H * hold_h / 8
        rows.append((bi, ct[bi], int(sim.t[k] + 60), s, net))
    return pd.DataFrame(rows, columns=["bar", "t", "exit_t", "side", "net"])


def fit(train):
    base = train["net"].mean(); model = {}
    for f in FEATS:
        x = train[f]
        if f in CAT:
            edges = None; b = x
        else:
            edges = np.unique(np.nanquantile(x, [0.2, 0.4, 0.6, 0.8])); b = np.digitize(x, edges)
        g = train.groupby(b)["net"].agg(["mean", "size"])
        model[f] = (edges, {k: (r["mean"] - base) * min(1.0, r["size"] / 50) for k, r in g.iterrows()})
    return model


def score(model, X):
    s = np.zeros(len(X))
    for f, (edges, tab) in model.items():
        b = X[f] if edges is None else np.digitize(X[f], edges)
        s += np.array([tab.get(k, 0.0) for k in b])
    return s


FEATS = ["hour4", "dow", "rsi", "dist_atr", "bw", "volr", "trend_agree", "mom12d", "atrp"]
summary = []
for sym in COINS:
    d1 = bt_data.load(sym, "1m"); sim = H.Sim(d1); B = H.resample(d1, 5); D = NS.build(B)
    side, risk, tpd = signal_arrays(B, D)
    F = features(B, D, d1)
    O = outcomes(sim, B, side, risk, tpd)
    X = F.iloc[O["bar"]].reset_index(drop=True)
    X["trend_agree"] = (X["trend"] * O["side"].to_numpy() > 0).astype(int)
    X["mom12d"] = X["mom12"] * O["side"].to_numpy()
    O = pd.concat([O, X], axis=1)
    wf0 = WF_START.timestamp()
    span = lambda T: T[T.entry_t >= wf0]

    # baseline, one position at a time, on the walk-forward span
    T0 = span(sim.run(B, side, risk, tpd, max_hold_min=HOLD))
    res = {"coin": sym, "signals": len(O), "base_n": len(T0), "base_win": (T0.net > 0).mean() * 100, "base_sum": T0.net.sum()}

    # in-sample "cheating": learn on everything, apply to everything
    m_all = fit(O); sc_all = score(m_all, O)
    for top in TOPS:
        thr = np.quantile(sc_all, 1 - top)
        keep = O.loc[sc_all >= thr, "bar"].to_numpy()
        s2 = np.zeros_like(side); s2[keep] = side[keep]
        T = span(sim.run(B, s2, risk, tpd, max_hold_min=HOLD))
        res[f"IS_top{int(top*100)}_n"] = len(T); res[f"IS_top{int(top*100)}_sum"] = T.net.sum()

    # walk-forward: quarterly refit on finished trades only
    quarters = pd.date_range(WF_START, pd.Timestamp("2026-10-01", tz="UTC"), freq="QS")
    for top in TOPS:
        s2 = np.zeros_like(side)
        for q0, q1 in zip(quarters, list(quarters[1:]) + [pd.Timestamp("2027-01-01", tz="UTC")]):
            a, b = q0.timestamp(), q1.timestamp()
            train = O[O.exit_t < a]
            test = O[(O.t >= a) & (O.t < b)]
            if len(train) < 300 or len(test) == 0:
                continue
            m = fit(train)
            thr = np.quantile(score(m, train), 1 - top)
            keep = test.loc[score(m, test) >= thr, "bar"].to_numpy()
            s2[keep] = side[keep]
        T = span(sim.run(B, s2, risk, tpd, max_hold_min=HOLD))
        H.check_trades(T)
        res[f"WF_top{int(top*100)}_n"] = len(T); res[f"WF_top{int(top*100)}_win"] = (T.net > 0).mean() * 100 if len(T) else np.nan
        res[f"WF_top{int(top*100)}_sum"] = T.net.sum()
        if top == 0.1:
            y = pd.to_datetime(T.entry_t, unit="s").dt.year
            res["WF_top10_by_year"] = T.groupby(y).net.sum().round(1).to_dict()
    summary.append(res)
    print(f"done {sym}", flush=True)

S = pd.DataFrame(summary)
print("\nAll sums are net % at 1x over 2024-01 -> 2026-10, ONE position at a time.\n")
print("== baseline (no filter) ==")
print(S[["coin", "signals", "base_n", "base_win", "base_sum"]].round(1).to_string(index=False))
print("\n== IN-SAMPLE learned filter (learned on the same trades it is scored on: looks good, is not real) ==")
print(S[["coin"] + [f"IS_top{t}_{k}" for t in (30, 20, 10) for k in ("n", "sum")]].round(1).to_string(index=False))
print("\n== WALK-FORWARD learned filter (learned only from finished past trades, refit every quarter) ==")
print(S[["coin"] + [f"WF_top{t}_{k}" for t in (30, 20, 10) for k in ("n", "win", "sum")]].round(1).to_string(index=False))
print("\nWF top10 per year:", S.set_index("coin")["WF_top10_by_year"].to_dict())
