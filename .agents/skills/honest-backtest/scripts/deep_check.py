"""Deep check of the shortlisted strategies: per-year, all exit settings, random-entry baseline,
and an independent plain-loop re-implementation of one configuration.
Usage (VPS):  PYTHONPATH=.:/tmp python /tmp/deep_check.py
"""
import numpy as np
import pandas as pd

import bt_harness as H
from strategy_signals import sig_donchian, sig_ema

pd.set_option("display.width", 220)
df3, info = H.load_3m()
sim = H.Sim(df3)
B = H.resample(df3, 240)
A = H.atr(B, 14).to_numpy()
rng = np.random.default_rng(7)

CANDS = {"4h donchian100": lambda: sig_donchian(B, 100), "4h ema20/50": lambda: sig_ema(B, 20, 50)}
EXITS = [(s, t) for s in (1.5, 2, 3) for t in (2, 3, 5, 8)]

for name, fn in CANDS.items():
    sg = np.asarray(fn()); sg[:210] = 0
    print(f"\n================ {name}  (raw signals: {(sg != 0).sum()})")
    rows = []
    for slm, tpm in EXITS:
        T = sim.run(B, sg, A * slm, A * tpm); H.check_trades(T)
        # random baseline: same number of signal bars, random bars and random direction, same exits
        idx = np.nonzero(sg)[0]
        rnd = []
        for _ in range(100):
            rs = np.zeros_like(sg); pick = rng.choice(np.arange(210, len(sg)), size=len(idx), replace=False)
            rs[pick] = rng.choice([-1, 1], size=len(idx))
            rnd.append(sim.run(B, rs, A * slm, A * tpm)["net"].sum())
        rnd = np.array(rnd)
        m, mi, mo = H.metrics(T), H.metrics(T, None, H.SPLIT), H.metrics(T, H.SPLIT)
        rows.append({"sl": slm, "tp": tpm, "n": m["n"], "win%": m["win%"], "ev%": m["ev%"], "sum%": m["sum%"],
                     "maxDD%": m["maxDD%"], "PF": m["PF"], "IS_sum": mi["sum%"], "OOS_sum": mo["sum%"],
                     "rand_med": np.median(rnd), "rand_p95": np.percentile(rnd, 95),
                     "beats_rand%": (rnd < m["sum%"]).mean() * 100, "open": m["open"]})
    print(pd.DataFrame(rows).round(2).to_string(index=False))

    # per-year for a middle-of-the-grid setting (not the best one)
    T = sim.run(B, sg, A * 2, A * 3)
    print(f"\n-- per year, SL 2xATR / TP 3xATR (middle setting, not the best) --")
    print(H.per_year(T).to_string())
    print("exit reasons:", T["reason"].value_counts().to_dict(), "| avg hold h:", round(T["hold_h"].mean(), 1),
          "| median SL distance %:", round(float(np.nanmedian(A * 2 / B["close"].to_numpy()) * 100), 2))

# ---------------- independent re-implementation (plain python loop over 3m candles) for donchian100 2/3
sg = np.asarray(sig_donchian(B, 100)); sg[:210] = 0
t3, o3, h3, l3, c3 = (df3[k].to_numpy() for k in ("time", "open", "high", "low", "close"))
pos_of = {int(t): i for i, t in enumerate(t3)}
ct = B["close_time"].to_numpy()
res, busy_until = [], -1
for bi in range(len(B)):
    if sg[bi] == 0 or ct[bi] < busy_until:
        continue
    j = pos_of.get(int(ct[bi]))
    if j is None:
        continue
    s, e = int(sg[bi]), o3[j]
    sl, tp = e - s * 2 * A[bi], e + s * 3 * A[bi]
    k = j
    while k < len(t3):
        hit_sl = l3[k] <= sl if s > 0 else h3[k] >= sl
        hit_tp = h3[k] >= tp if s > 0 else l3[k] <= tp
        if hit_sl or hit_tp:
            break
        k += 1
    if k == len(t3):
        res.append(("OPEN", int(t3[j]))); break
    if hit_sl:
        x = o3[k] if (k > j and ((s > 0 and o3[k] <= sl) or (s < 0 and o3[k] >= sl))) else sl
    else:
        x = tp
    res.append(("SL" if hit_sl else "TP", int(t3[j]), round(s * (x / e - 1) * 100, 6)))
    busy_until = t3[k] + 180
T = sim.run(B, sg, A * 2, A * 3)
h_list = [(r, int(et), round(g, 6)) for r, et, g in zip(T.reason, T.entry_t, T.gross) if r != "OPEN"]
i_list = [r for r in res if r[0] != "OPEN"]
print(f"\nINDEPENDENT CHECK donchian100 2/3: harness {len(h_list)} closed trades, plain loop {len(i_list)}; "
      f"identical: {h_list == i_list}")
