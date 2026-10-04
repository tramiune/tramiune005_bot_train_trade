"""Cross-coin test of the XRP 5m NW + RSI + Volume signal with the ORIGINAL parameters (no re-tuning),
R:R 2-3 exits. Each coin: one position at a time, next-bar-open entry, exits on 1m, SL first,
taker + slippage + funding. IS < 2025-01-01 <= OOS.
Usage (repo root): web_app/backend/.venv/bin/python .agents/skills/honest-backtest/scripts/nada_cross_coin.py
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
COINS = ["XRPUSDT", "DOGEUSDT", "SOLUSDT", "ETHUSDT", "BTCUSDT"]
EXITS = list(itertools.product([0.75, 1.0, 1.5, 2.0], [2.0, 2.5, 3.0]))  # (SL%, RR)

rows, trades = [], {}
for sym in COINS:
    d1 = bt_data.load(sym, "1m")
    sim = H.Sim(d1)
    B = H.resample(d1, 5)
    X.signals.__defaults__[-1].clear()  # RSI cache is keyed per bar set; clear between coins to be safe
    side = X.signals(B)
    c = B["close"].to_numpy()
    for sl, rr in EXITS:
        T = sim.run(B, side, c * sl / 100, c * sl * rr / 100)
        H.check_trades(T)
        T["coin"] = sym
        trades[(sym, sl, rr)] = T
        ma, mi, mo = H.metrics(T), H.metrics(T, None, H.SPLIT), H.metrics(T, H.SPLIT)
        rows.append({"coin": sym, "sl%": sl, "rr": rr, "signals": int((side != 0).sum()), "n": ma.get("n", 0),
                     "win%": ma.get("win%"), "ev%": ma.get("ev%"), "sum%": ma.get("sum%"), "maxDD%": ma.get("maxDD%"),
                     "IS_sum": mi.get("sum%", 0), "OOS_sum": mo.get("sum%", 0), "hold_h": ma.get("hold_h")})
R = pd.DataFrame(rows)
R.to_csv(os.path.join(bt_data.ROOT, "nada_cross_coin.csv"), index=False)
print("== per coin, per exit (original signal parameters, nothing re-tuned) ==")
print(R.round(2).to_string(index=False))
print("\n== per coin, median over the 12 exits ==")
print(R.groupby("coin").agg(signals=("signals", "first"), n=("n", "median"), win=("win%", "median"),
                            ev=("ev%", "median"), IS=("IS_sum", "median"), OOS=("OOS_sum", "median"),
                            pos_both=("IS_sum", lambda s: int(((s > 0) & (R.loc[s.index, "OOS_sum"] > 0)).sum()))).round(2).to_string())
print("\n== POOLED over the 5 coins, per exit ==")
for sl, rr in EXITS:
    P = pd.concat([trades[(s, sl, rr)] for s in COINS])
    r = P["net"].to_numpy()
    print(f"SL {sl}% RR {rr}: trades {len(P)}, win {(r>0).mean()*100:.1f}%, EV {r.mean():.3f}%/trade, "
          f"IS {P.loc[P.entry_t < H.SPLIT,'net'].sum():.1f}%, OOS {P.loc[P.entry_t >= H.SPLIT,'net'].sum():.1f}%, "
          f"coins positive {sum(trades[(s, sl, rr)]['net'].sum() > 0 for s in COINS)}/5")
