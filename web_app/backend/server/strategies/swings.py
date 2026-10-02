from __future__ import annotations

import pandas as pd


def pivot_high(high: pd.Series, left: int, right: int) -> pd.Series:
    out = pd.Series(False, index=high.index)
    for i in range(left, len(high) - right):
        window = high.iloc[i - left : i + right + 1]
        if high.iloc[i] == window.max() and (window == high.iloc[i]).sum() == 1:
            out.iloc[i] = True
    return out


def pivot_low(low: pd.Series, left: int, right: int) -> pd.Series:
    out = pd.Series(False, index=low.index)
    for i in range(left, len(low) - right):
        window = low.iloc[i - left : i + right + 1]
        if low.iloc[i] == window.min() and (window == low.iloc[i]).sum() == 1:
            out.iloc[i] = True
    return out
