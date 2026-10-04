"""Honest backtest harness for DOGEUSDT (Binance USD-M Futures) strategies.

Rules enforced here (see ../SKILL.md for the reasons):
- strictly ONE position at a time; signals while a position is open are ignored
- no silent horizon cap: a trade runs until TP/SL, or until an EXPLICIT time-stop that closes
  at market and is counted; a trade still open at the end of data is marked to market and flagged
- signal on a CLOSED bar, entry at the open of the next 3m candle (no look-ahead)
- exits are checked on 3m candles; TP and SL in the same candle -> SL first; gap through SL -> fill at open
- costs: taker fee + slippage on both sides + funding charged against every position
- metrics split into in-sample / out-of-sample
Run on the VPS from web_app/backend with the venv:  PYTHONPATH=. python <script using this module>
"""
import sqlite3

import numpy as np
import pandas as pd

DB = "trading_bot.db"
TABLE = "klines_dogeusdt_3m"
FEE_SIDE = 0.05        # % Binance USD-M taker fee per side
SLIP_SIDE = 0.02       # % slippage per side
FUNDING_PER_8H = 0.01  # % charged against every open position (conservative, sign ignored)
SPLIT = pd.Timestamp("2025-01-01", tz="UTC").timestamp()  # in-sample < SPLIT <= out-of-sample
STEP = 180             # seconds per 3m candle


# ---------------------------------------------------------------- data
def load_3m(db=DB):
    con = sqlite3.connect(db)
    df = pd.read_sql(f"SELECT time, open, high, low, close, volume FROM {TABLE} ORDER BY time", con)
    d = np.diff(df["time"].to_numpy())
    assert (d > 0).all(), "duplicate / unsorted timestamps in 3m table"
    info = {"candles": len(df), "gaps": int((d != STEP).sum()),
            "from": pd.to_datetime(df.time.iloc[0], unit="s"), "to": pd.to_datetime(df.time.iloc[-1], unit="s")}
    return df, info


def resample(df3, minutes):
    """Aggregate 3m candles into complete `minutes` bars (incomplete/gappy buckets are dropped)."""
    if minutes == 3:
        out = df3.copy()
    else:
        sec = minutes * 60
        b = (df3["time"] // sec) * sec
        g = df3.groupby(b)
        out = pd.DataFrame({
            "time": g["time"].first().index.to_numpy(),
            "open": g["open"].first().to_numpy(), "high": g["high"].max().to_numpy(),
            "low": g["low"].min().to_numpy(), "close": g["close"].last().to_numpy(),
            "volume": g["volume"].sum().to_numpy(), "n": g.size().to_numpy(),
        })
        out = out[out["n"] == minutes // 3].drop(columns="n")
    out["close_time"] = out["time"] + minutes * 60
    return out.reset_index(drop=True)


# ---------------------------------------------------------------- indicators (closed-bar only)
def ema(s, n):
    return s.ewm(span=n, adjust=False).mean()


def atr(bars, n=14):
    h, l, c = bars["high"], bars["low"], bars["close"]
    tr = np.maximum(h - l, np.maximum((h - c.shift()).abs(), (l - c.shift()).abs()))
    return tr.ewm(alpha=1 / n, adjust=False).mean()


def rsi(s, n=14):
    d = s.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn)


# ---------------------------------------------------------------- simulation
class Sim:
    def __init__(self, df3):
        self.t = df3["time"].to_numpy()
        self.o = df3["open"].to_numpy()
        self.h = df3["high"].to_numpy()
        self.l = df3["low"].to_numpy()
        self.c = df3["close"].to_numpy()
        self.n = len(self.t)

    def _first_hit(self, j, end, s, sl, tp):
        pos, chunk = j, 512
        while pos < end:
            stop = min(end, pos + chunk)
            hh, ll = self.h[pos:stop], self.l[pos:stop]
            if s > 0:
                hs, ht = ll <= sl, hh >= tp
            else:
                hs, ht = hh >= sl, ll <= tp
            m = hs | ht
            if m.any():
                q = int(np.argmax(m))
                return pos + q, bool(hs[q])  # SL wins a same-candle double touch
            pos, chunk = stop, chunk * 2
        return None, None

    def run(self, bars, side, sl_dist, tp_dist, max_hold_min=None):
        """side: +1/-1/0 per bar (decided at bar close). sl_dist/tp_dist: absolute price distance per bar."""
        side = np.asarray(side)
        close_t = bars["close_time"].to_numpy()
        sig = np.nonzero(side != 0)[0]
        j_all = np.searchsorted(self.t, close_t[sig], "left")
        max_c = None if max_hold_min is None else max(1, int(max_hold_min * 60 // STEP))
        trades, free_t = [], -1
        for k, bi in enumerate(sig):
            ct = close_t[bi]
            if ct < free_t:
                continue  # a position is still open -> signal ignored
            j = int(j_all[k])
            if j >= self.n:
                break
            if self.t[j] != ct:
                continue  # data gap right after the signal: cannot enter at a known price
            s = int(side[bi]); e = self.o[j]
            sd, td = float(sl_dist[bi]), float(tp_dist[bi])
            if not (sd > 0 and td > 0):
                continue
            sl, tp = e - s * sd, e + s * td
            end = self.n if max_c is None else min(self.n, j + max_c)
            k_hit, is_sl = self._first_hit(j, end, s, sl, tp)
            if k_hit is not None:
                if is_sl:
                    gap = (self.o[k_hit] <= sl) if s > 0 else (self.o[k_hit] >= sl)
                    x = self.o[k_hit] if (gap and k_hit > j) else sl
                    reason = "SL"
                else:
                    x, reason = tp, "TP"
                xi = k_hit
            elif end < self.n:
                xi, x, reason = end - 1, self.c[end - 1], "TIME"
            else:
                xi, x, reason = self.n - 1, self.c[-1], "OPEN"  # unfinished: mark to market
            hold_h = (self.t[xi] + STEP - self.t[j]) / 3600
            gross = s * (x / e - 1) * 100
            net = gross - 2 * (FEE_SIDE + SLIP_SIDE) - FUNDING_PER_8H * hold_h / 8
            trades.append((int(self.t[j]), int(self.t[xi] + STEP), s, e, x, reason, gross, net, hold_h))
            free_t = self.t[xi] + STEP
            if reason == "OPEN":
                break
        return pd.DataFrame(trades, columns=["entry_t", "exit_t", "side", "entry", "exit", "reason",
                                             "gross", "net", "hold_h"])


# ---------------------------------------------------------------- checks & metrics
def check_trades(T):
    """Independent sanity checks; raise if a rule is violated."""
    if len(T) == 0:
        return
    assert (T["entry_t"].to_numpy()[1:] >= T["exit_t"].to_numpy()[:-1]).all(), "overlapping trades"
    assert (T["exit_t"] > T["entry_t"]).all(), "exit before entry"
    assert (T["reason"] == "OPEN").sum() <= 1 and (T["reason"].iloc[:-1] != "OPEN").all(), "OPEN not last"


def metrics(T, t_from=None, t_to=None):
    if t_from is not None:
        T = T[T["entry_t"] >= t_from]
    if t_to is not None:
        T = T[T["entry_t"] < t_to]
    n = len(T)
    if n == 0:
        return {"n": 0}
    r = T["net"].to_numpy()
    eq = np.cumprod(1 + r / 100)
    dd = (1 - eq / np.maximum.accumulate(eq)).max() * 100
    pos, neg = r[r > 0].sum(), -r[r < 0].sum()
    months = max((T["exit_t"].iloc[-1] - T["entry_t"].iloc[0]) / (86400 * 30.44), 1e-9)
    return {"n": n, "win%": (r > 0).mean() * 100, "ev%": r.mean(), "sum%": r.sum(),
            "comp%": (eq[-1] - 1) * 100, "maxDD%": dd, "PF": pos / neg if neg > 0 else np.inf,
            "hold_h": T["hold_h"].mean(), "tr/mo": n / months, "open": int((T["reason"] == "OPEN").sum())}


def per_year(T):
    y = pd.to_datetime(T["entry_t"], unit="s").dt.year
    return T.groupby(y)["net"].agg(n="size", win=lambda s: (s > 0).mean() * 100, sum="sum").round(1)
