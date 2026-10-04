"""Signal definitions (events decided on CLOSED bars, no look-ahead). +1 long, -1 short, 0 none."""
import numpy as np
import pandas as pd

import bt_harness as H


# ---------------------------------------------------------------- signal definitions (events on closed bars)
def cross_up(a, b):
    return (a > b) & (a.shift(1) <= b.shift(1))


def sig_donchian(B, n):
    up = B["high"].rolling(n).max().shift(1)
    dn = B["low"].rolling(n).min().shift(1)
    return np.where(cross_up(B["close"], up), 1, np.where(cross_up(-B["close"], -dn), -1, 0))


def sig_ema(B, f, s):
    ef, es = H.ema(B["close"], f), H.ema(B["close"], s)
    return np.where(cross_up(ef, es), 1, np.where(cross_up(es, ef), -1, 0))


def sig_rsi(B, lo, trend):
    r = H.rsi(B["close"], 14)
    L = cross_up(r, pd.Series(lo, index=r.index))          # RSI leaves oversold
    S = cross_up(pd.Series(100 - lo, index=r.index), r)    # RSI leaves overbought
    if trend:
        e = H.ema(B["close"], 200)
        L, S = L & (B["close"] > e), S & (B["close"] < e)
    return np.where(L, 1, np.where(S, -1, 0))


def sig_bb(B, trend):
    m = B["close"].rolling(20).mean(); sd = B["close"].rolling(20).std()
    L = cross_up(B["close"], m - 2 * sd)                    # back inside from below
    S = cross_up(m + 2 * sd, B["close"])                    # back inside from above
    if trend:
        e = H.ema(B["close"], 200)
        L, S = L & (B["close"] > e), S & (B["close"] < e)
    return np.where(L, 1, np.where(S, -1, 0))


def sig_squeeze(B, follow):
    """Same squeeze-fire event as DOGE_3M_DEGEN. follow=False -> its contrarian direction."""
    c, h, l = B["close"], B["high"], B["low"]
    tr = np.maximum(h - l, np.maximum((h - c.shift()).abs(), (l - c.shift()).abs()))
    a = tr.rolling(20).mean(); mid = c.rolling(20).mean(); sd = c.rolling(20).std()
    on = (mid + 2 * sd < mid + 1.5 * a) & (mid - 2 * sd > mid - 1.5 * a)
    dur = on.groupby((~on).cumsum()).cumsum()
    fire = (~on) & on.shift(1, fill_value=False) & (dur.shift(1) >= 5) & (B["volume"] > 1.5 * B["volume"].rolling(20).mean())
    bull = c > mid
    d = np.where(bull, 1, -1) * (1 if follow else -1)
    return np.where(fire, d, 0)
