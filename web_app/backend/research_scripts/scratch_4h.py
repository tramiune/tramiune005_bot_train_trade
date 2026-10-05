import itertools
import os
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(".agents/skills/honest-backtest/scripts"))
import bt_data
import bt_harness as H
from strategy_signals import sig_donchian

pd.set_option("display.width", 250)
sym = "DOGEUSDT"

print("Downloading 1m data (might take a minute)...")
bt_data.download(sym, "1m", "2022-09")

print("Loading data...")
d1 = bt_data.load(sym, "1m")
sim = H.Sim(d1)
B = H.resample(d1, 240)
A = H.atr(B, 14).to_numpy()

print("Simulating...")
n = 100
slm, tpm = 1.5, 3.0
sg = np.asarray(sig_donchian(B, n)); sg[:210] = 0
T = sim.run(B, sg, A * slm, A * tpm)
H.check_trades(T)
ma, mi, mo = H.metrics(T), H.metrics(T, None, H.SPLIT), H.metrics(T, H.SPLIT)

row = {"coin": sym, "N": n, "sl_atr": slm, "tp_atr": tpm, "rr": tpm / slm, "n": ma.get("n", 0),
       "win%": ma.get("win%"), "ev%": ma.get("ev%"), "sum%": ma.get("sum%"), "maxDD%": ma.get("maxDD%"),
       "IS_sum": mi.get("sum%", 0), "OOS_sum": mo.get("sum%", 0), "tr/mo": ma.get("tr/mo")}

print(pd.DataFrame([row]).round(2).to_string(index=False))
