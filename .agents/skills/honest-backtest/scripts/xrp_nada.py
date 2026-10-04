"""TradingView strategy "XRP => Nada + RSI + Volume" ported 1:1, tested on XRPUSDT USD-M futures 5m.

Pine logic reproduced:
  out   = sum_{i=0..499} close[i] * gauss(i, h) / sum(gauss)      (causal Nadaraya-Watson, h=8)
  mae   = sma(|close - out|, 499) * mult                            (mult=3)
  BUY   : crossunder(close, lower) and rsi(14) < 20 and not (volume > sma(volume,20) * 2)
  SELL  : crossover(close, upper)  and rsi(14) > 80 and not high volume
Signals are decided on the CLOSED 5m bar; entry at the next bar open (TradingView default).

Tests:
  1) ORIGINAL: no TP/SL, always in market, reverse on the opposite signal (Pine strategy.entry).
  2) TP/SL % grid, one position at a time (signals ignored while open), exits checked on 1m candles,
     SL first on same-candle double touch, taker fee + slippage both sides + funding.
     TP/SL chosen on in-sample (< 2025-01-01) only; out-of-sample reported.
Usage (repo root): web_app/backend/.venv/bin/python .agents/skills/honest-backtest/scripts/xrp_nada.py
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
pd.set_option("display.max_columns", 40)
SYMBOL = os.environ.get("SYMBOL", "XRPUSDT")
H_BW, MULT, RSI_LEN, RSI_OB, RSI_OS, VOL_MULT = 8.0, 3.0, 14, 80, 20, 2.0


def pine_rsi(src, n):
    """ta.rsi: RMA seeded with the SMA of the first n changes."""
    d = np.diff(src, prepend=np.nan)
    up, dn = np.clip(d, 0, None), np.clip(-d, 0, None)
    out = np.full(len(src), np.nan)
    if len(src) <= n:
        return out
    au, ad = np.nanmean(up[1:n + 1]), np.nanmean(dn[1:n + 1])
    out[n] = 100 if ad == 0 else 100 - 100 / (1 + au / ad)
    for i in range(n + 1, len(src)):
        au = (au * (n - 1) + up[i]) / n
        ad = (ad * (n - 1) + dn[i]) / n
        out[i] = 100 if ad == 0 else 100 - 100 / (1 + au / ad)
    return out


def signals(B):
    c = B["close"].to_numpy()
    w = np.exp(-(np.arange(500) ** 2) / (H_BW * H_BW * 2))
    out = np.convolve(c, w)[: len(c)] / w.sum()
    out[:499] = np.nan                                   # Pine: src[i] is na for the first 499 bars
    mae = pd.Series(np.abs(c - out)).rolling(499).mean().to_numpy() * MULT
    upper, lower = out + mae, out - mae
    r = pine_rsi(c, RSI_LEN)
    v = B["volume"].to_numpy()
    high_vol = v > pd.Series(v).rolling(20).mean().to_numpy() * VOL_MULT
    prev_c, prev_l, prev_u = np.roll(c, 1), np.roll(lower, 1), np.roll(upper, 1)
    cross_dn = (c < lower) & (prev_c >= prev_l)
    cross_up = (c > upper) & (prev_c <= prev_u)
    buy = cross_dn & (r < RSI_OS) & ~high_vol
    sell = cross_up & (r > RSI_OB) & ~high_vol
    side = np.where(buy, 1, np.where(sell, -1, 0))
    side[:1000] = 0
    return side


def original_reversal(sim, B, side):
    """Always in the market, flip on the opposite signal (no TP/SL), taker costs on each fill."""
    ct = B["close_time"].to_numpy()
    idx = np.nonzero(side)[0]
    trades, pos, e, et = [], 0, 0.0, 0
    for bi in idx:
        s = int(side[bi])
        if s == pos:
            continue  # pyramiding = 0: same-direction signal ignored
        j = np.searchsorted(sim.t, ct[bi])
        if j >= sim.n or sim.t[j] != ct[bi]:
            continue
        px = sim.o[j]
        if pos != 0:
            hold_h = (sim.t[j] - et) / 3600
            gross = pos * (px / e - 1) * 100
            trades.append((et, int(sim.t[j]), pos, e, px, "REV", gross,
                           gross - 2 * (H.FEE_SIDE + H.SLIP_SIDE) - H.FUNDING_PER_8H * hold_h / 8, hold_h))
        pos, e, et = s, px, int(sim.t[j])
    if pos != 0:
        hold_h = (sim.t[-1] + sim.step - et) / 3600
        gross = pos * (sim.c[-1] / e - 1) * 100
        trades.append((et, int(sim.t[-1] + sim.step), pos, e, sim.c[-1], "OPEN", gross,
                       gross - 2 * (H.FEE_SIDE + H.SLIP_SIDE) - H.FUNDING_PER_8H * hold_h / 8, hold_h))
    return pd.DataFrame(trades, columns=["entry_t", "exit_t", "side", "entry", "exit", "reason", "gross", "net", "hold_h"])


def fmt(m):
    return {k: (round(v, 2) if isinstance(v, float) else v) for k, v in m.items()}


if __name__ == "__main__":
    d1 = bt_data.load(SYMBOL, "1m")
    dd = np.diff(d1["time"].to_numpy())
    print(f"{SYMBOL} 1m futures: {len(d1)} candles, gaps {(dd != 60).sum()}, dups {(dd <= 0).sum()}, "
          f"{pd.to_datetime(d1.time.iloc[0], unit='s')} -> {pd.to_datetime(d1.time.iloc[-1], unit='s')}")
    sim = H.Sim(d1)
    B = H.resample(d1, 5)
    side = signals(B)
    nb, ns = int((side > 0).sum()), int((side < 0).sum())
    yrs = pd.to_datetime(B["close_time"][side != 0], unit="s").dt.year.value_counts().sort_index().to_dict()
    print(f"raw signals: {nb} BUY, {ns} SELL | per year {yrs}")

    print("\n== 1) ORIGINAL script (no TP/SL, reverse on opposite signal) ==")
    T0 = original_reversal(sim, B, side)
    print("ALL", fmt(H.metrics(T0)), "\nIS ", fmt(H.metrics(T0, None, H.SPLIT)), "\nOOS", fmt(H.metrics(T0, H.SPLIT)))
    print("gross EV % per trade (before costs):", round(T0["gross"].mean(), 4))

    print("\n== 2) TP/SL % grid, one position at a time ==")
    c = B["close"].to_numpy()
    TPS = [0.3, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0]
    SLS = [0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0, 7.0, 10.0]
    rows, store = [], {}
    for tp, sl in itertools.product(TPS, SLS):
        T = sim.run(B, side, c * sl / 100, c * tp / 100)
        H.check_trades(T)
        store[(tp, sl)] = T
        mi, mo = H.metrics(T, None, H.SPLIT), H.metrics(T, H.SPLIT)
        rows.append({"tp%": tp, "sl%": sl, "IS_n": mi.get("n", 0), "IS_win": mi.get("win%"), "IS_ev": mi.get("ev%"),
                     "IS_sum": mi.get("sum%"), "IS_dd": mi.get("maxDD%"), "IS_pf": mi.get("PF"),
                     "OOS_n": mo.get("n", 0), "OOS_win": mo.get("win%"), "OOS_ev": mo.get("ev%"),
                     "OOS_sum": mo.get("sum%"), "OOS_dd": mo.get("maxDD%"), "OOS_pf": mo.get("PF"),
                     "gross_ev": T["gross"].mean(), "open": int((T["reason"] == "OPEN").sum()),
                     "hold_h": T["hold_h"].mean()})
    R = pd.DataFrame(rows)
    R.to_csv(os.path.join(bt_data.ROOT, f"xrp_nada_grid_{SYMBOL}.csv"), index=False)
    print(f"combos: {len(R)} | IS ev>0: {(R.IS_ev > 0).sum()} | OOS ev>0: {(R.OOS_ev > 0).sum()} | "
          f"both: {((R.IS_ev > 0) & (R.OOS_ev > 0)).sum()} | gross ev>0 (all period): {(R.gross_ev > 0).sum()}")
    print("\nOOS EV % per trade (rows = TP%, cols = SL%):")
    print(R.pivot(index="tp%", columns="sl%", values="OOS_ev").round(3).to_string())
    print("\nIS EV % per trade (rows = TP%, cols = SL%):")
    print(R.pivot(index="tp%", columns="sl%", values="IS_ev").round(3).to_string())
    print("\nWIN RATE all period % (rows = TP%, cols = SL%):")
    R["all_win"] = [(store[(a, b)]["net"] > 0).mean() * 100 for a, b in zip(R["tp%"], R["sl%"])]
    print(R.pivot(index="tp%", columns="sl%", values="all_win").round(1).to_string())

    sel = R[R.IS_n >= 25].sort_values("IS_pf", ascending=False).head(10)
    print("\n== top 10 chosen on IN-SAMPLE only (IS_n>=25, by IS PF) -> OUT-OF-SAMPLE ==")
    print(sel.round(3).to_string(index=False))

    rng = np.random.default_rng(11)
    k = int((side != 0).sum())
    picks = [(float(sel.iloc[0]["tp%"]), float(sel.iloc[0]["sl%"])), (0.5, 3.0), (0.75, 2.0), (1.0, 3.0), (2.0, 2.0)]
    for tp, sl in dict.fromkeys(picks):
        T = store[(tp, sl)]
        r = T["net"].to_numpy()
        boot = np.array([rng.choice(r, size=len(r), replace=True).mean() for _ in range(5000)])
        rnd = []
        for _ in range(300):
            rs = np.zeros_like(side)
            rs[rng.choice(np.arange(1000, len(side)), size=k, replace=False)] = rng.choice([-1, 1], size=k)
            rnd.append(sim.run(B, rs, c * sl / 100, c * tp / 100)["net"].mean())
        rnd = np.array(rnd)
        m = H.metrics(T)
        print(f"\n-- TP {tp}% / SL {sl}%: n={m['n']} win={m['win%']:.1f}% EV={m['ev%']:.3f}%/trade sum={m['sum%']:.1f}% "
              f"maxDD={m['maxDD%']:.1f}% PF={m['PF']:.2f} hold={m['hold_h']:.1f}h open={m['open']}")
        print(f"   90% bootstrap CI of EV: [{np.percentile(boot, 5):.3f}, {np.percentile(boot, 95):.3f}]  "
              f"P(EV<=0) ~ {(boot <= 0).mean()*100:.1f}%")
        print(f"   random entries same TP/SL (300 runs): median EV {np.median(rnd):.3f}%, 95th pct {np.percentile(rnd, 95):.3f}% "
              f"-> strategy beats {(rnd < r.mean()).mean()*100:.0f}% of random runs")
        print("   per year:", H.per_year(T).to_dict("index"))
