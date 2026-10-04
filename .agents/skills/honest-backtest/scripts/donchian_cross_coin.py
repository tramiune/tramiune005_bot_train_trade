"""Cross-coin test of 4h Donchian breakout (1 indicator + ATR for SL/TP), parameters NOT re-tuned per coin.
R:R >= 2 exits. Same honest rules (next-bar-open entry, exits on 1m, SL first, taker+slip+funding).
Usage (repo root): web_app/backend/.venv/bin/python .agents/skills/honest-backtest/scripts/donchian_cross_coin.py
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
COINS = ["DOGEUSDT", "XRPUSDT", "SOLUSDT", "ETHUSDT", "BTCUSDT"]
NS = [55, 100]
EXITS = [(1.5, 3.0), (1.5, 4.5), (2.0, 4.0), (2.0, 6.0)]  # (SL xATR, TP xATR): RR 2 and 3

rows, trades = [], {}
for sym in COINS:
    d1 = bt_data.load(sym, "1m")
    sim = H.Sim(d1)
    B = H.resample(d1, 240)
    A = H.atr(B, 14).to_numpy()
    for n in NS:
        sg = np.asarray(sig_donchian(B, n)); sg[:210] = 0
        for slm, tpm in EXITS:
            T = sim.run(B, sg, A * slm, A * tpm)
            H.check_trades(T)
            trades[(sym, n, slm, tpm)] = T
            ma, mi, mo = H.metrics(T), H.metrics(T, None, H.SPLIT), H.metrics(T, H.SPLIT)
            rows.append({"coin": sym, "N": n, "sl_atr": slm, "tp_atr": tpm, "rr": tpm / slm, "n": ma.get("n", 0),
                         "win%": ma.get("win%"), "ev%": ma.get("ev%"), "sum%": ma.get("sum%"), "maxDD%": ma.get("maxDD%"),
                         "IS_sum": mi.get("sum%", 0), "OOS_sum": mo.get("sum%", 0), "tr/mo": ma.get("tr/mo")})
R = pd.DataFrame(rows)
print(R.round(2).to_string(index=False))
print("\n== pooled over 5 coins ==")
for n, (slm, tpm) in itertools.product(NS, EXITS):
    P = pd.concat([trades[(s, n, slm, tpm)] for s in COINS]); r = P["net"].to_numpy()
    yr = P.groupby(pd.to_datetime(P.entry_t, unit="s").dt.year)["net"].sum().round(0).to_dict()
    print(f"Donchian{n} SL {slm}ATR TP {tpm}ATR (RR {tpm/slm:.0f}): trades {len(P)}, win {(r>0).mean()*100:.1f}%, "
          f"EV {r.mean():.3f}%, IS {P.loc[P.entry_t < H.SPLIT,'net'].sum():.0f}%, OOS {P.loc[P.entry_t >= H.SPLIT,'net'].sum():.0f}%, "
          f"coins positive {sum(trades[(s, n, slm, tpm)]['net'].sum() > 0 for s in COINS)}/5 | per year {yr}")
