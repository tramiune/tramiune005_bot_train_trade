from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from ...chart_serializers import df_to_lwc
from ...market_data import fetch_ohlcv_ccxt
from ..pnl import simulate_swing_targets
from ..swings import pivot_high, pivot_low
from .constants import DEFAULT_FIB_HIGH, DEFAULT_FIB_LOW, MIN_BARS, STRATEGY_ID


def _golden_zone_up(high: float, low: float, fib_lo: float, fib_hi: float) -> Tuple[float, float]:
    """Pullback down from high: zone between fib_hi (deeper) and fib_lo (shallower)."""
    rng = high - low
    zone_hi = high - fib_lo * rng
    zone_lo = high - fib_hi * rng
    return zone_lo, zone_hi


def _golden_zone_down(high: float, low: float, fib_lo: float, fib_hi: float) -> Tuple[float, float]:
    """Pullback up from low: zone between fib_lo and fib_hi above low."""
    rng = high - low
    zone_lo = low + fib_lo * rng
    zone_hi = low + fib_hi * rng
    return zone_lo, zone_hi


def _bar_touches_zone(low: float, high: float, zone_lo: float, zone_hi: float) -> bool:
    return low <= zone_hi and high >= zone_lo


def _fib_levels_up(high: float, low: float) -> Dict[str, float]:
    rng = high - low
    return {
        "0": high,
        "0.382": high - 0.382 * rng,
        "0.5": high - 0.5 * rng,
        "0.618": high - 0.618 * rng,
        "1": low,
    }


def _impulse_pct(high: float, low: float) -> float:
    lo = min(high, low)
    if lo <= 0:
        return 0.0
    return abs(high - low) / lo * 100.0


def _dedupe_nearby_signals(signals: List[Dict[str, Any]], spacing_bars: int) -> List[Dict[str, Any]]:
    """Trong vùng sideway: gom tín hiệu gần nhau, giữ impulse mạnh nhất (tránh BUY+SELL cạnh nhau)."""
    if spacing_bars <= 0 or len(signals) <= 1:
        return signals
    ordered = sorted(signals, key=lambda s: int(s["entry_idx"]))
    clusters: List[List[Dict[str, Any]]] = [[ordered[0]]]
    for s in ordered[1:]:
        if int(s["entry_idx"]) - int(clusters[-1][-1]["entry_idx"]) <= spacing_bars:
            clusters[-1].append(s)
        else:
            clusters.append([s])
    out: List[Dict[str, Any]] = []
    for cluster in clusters:
        out.append(max(cluster, key=lambda x: float(x.get("impulse_pct", 0))))
    return out


def _fib_levels_down(high: float, low: float) -> Dict[str, float]:
    rng = high - low
    return {
        "0": low,
        "0.382": low + 0.382 * rng,
        "0.5": low + 0.5 * rng,
        "0.618": low + 0.618 * rng,
        "1": high,
    }


def run_fib_golden_pocket_backtest(
    *,
    symbol: str,
    timeframe: str,
    days_back: int,
    exchange: str,
    limit: int,
    pivot_left: int = 5,
    pivot_right: int = 5,
    min_impulse_pct: float = 1.5,
    min_impulse_bars: int = 8,
    max_pullback_bars: int = 120,
    fib_zone_low: float = DEFAULT_FIB_LOW,
    fib_zone_high: float = DEFAULT_FIB_HIGH,
    require_bullish_close: bool = True,
    require_bearish_close: bool = True,
    max_setups_draw: int = 8,
    min_signal_spacing_bars: int = 24,
    stake_usd: float = 100.0,
    starting_bankroll_usd: float = 1000.0,
) -> Dict[str, Any]:
    since = datetime.now(timezone.utc) - timedelta(days=int(days_back))
    df = fetch_ohlcv_ccxt(exchange, symbol.upper(), timeframe, since=since, limit=int(limit))
    if df.empty or len(df) < MIN_BARS:
        return {"error": "no_data", "message": f"need at least {MIN_BARS} candles"}

    if fib_zone_low >= fib_zone_high:
        return {"error": "invalid_params", "message": "fib_zone_low must be < fib_zone_high"}

    open_ = df["open"].astype(float).values
    high = df["high"].astype(float).values
    low = df["low"].astype(float).values
    close = df["close"].astype(float).values
    times = df["timestamp"]
    n = len(df)

    ph = pivot_high(pd.Series(high), int(pivot_left), int(pivot_right))
    pl = pivot_low(pd.Series(low), int(pivot_left), int(pivot_right))

    pivots: List[Tuple[int, str, float]] = []
    for i in range(n):
        if bool(ph.iloc[i]):
            pivots.append((i, "H", float(high[i])))
        if bool(pl.iloc[i]):
            pivots.append((i, "L", float(low[i])))

    signals: List[Dict[str, Any]] = []
    markers: List[Dict[str, Any]] = []
    setups_draw: List[Dict[str, Any]] = []
    used_impulses_set: set = set()

    def _add_setup_draw(
        direction: str,
        anchor_start: int,
        anchor_end: int,
        price_0: float,
        price_1: float,
        zone_lo: float,
        zone_hi: float,
        signal_idx: int,
    ) -> None:
        if len(setups_draw) >= int(max_setups_draw):
            return
        t0 = int(pd.to_datetime(times.iloc[anchor_start], utc=True).timestamp())
        t1 = int(pd.to_datetime(times.iloc[min(signal_idx + 20, n - 1)], utc=True).timestamp())
        hi_p = max(price_0, price_1)
        lo_p = min(price_0, price_1)
        levels = _fib_levels_up(hi_p, lo_p) if direction == "up" else _fib_levels_down(hi_p, lo_p)
        setups_draw.append(
            {
                "direction": direction,
                "from_time": t0,
                "to_time": t1,
                "anchor_start_idx": anchor_start,
                "anchor_end_idx": anchor_end,
                "price_0": price_0,
                "price_1": price_1,
                "zone_low": zone_lo,
                "zone_high": zone_hi,
                "levels": levels,
            }
        )

    for k in range(len(pivots) - 1):
        i0, t0, p0 = pivots[k]
        i1, t1, p1 = pivots[k + 1]

        # Bullish impulse: Low -> High, then pullback into golden pocket -> BUY
        if t0 == "L" and t1 == "H" and i1 > i0:
            impulse_key = (i0, i1)
            if impulse_key in used_impulses_set:
                continue
            if i1 - i0 < int(min_impulse_bars):
                continue
            lo_p, hi_p = p0, p1
            imp_pct = _impulse_pct(hi_p, lo_p)
            if imp_pct < float(min_impulse_pct):
                continue

            zone_lo, zone_hi = _golden_zone_up(hi_p, lo_p, float(fib_zone_low), float(fib_zone_high))
            scan_start = i1 + int(pivot_right)
            scan_end = min(n - 2, i1 + int(max_pullback_bars))
            fired = False

            for j in range(scan_start, scan_end + 1):
                if not _bar_touches_zone(low[j], high[j], zone_lo, zone_hi):
                    continue
                bullish = close[j] > open_[j]
                in_zone_close = zone_lo <= close[j] <= zone_hi
                if require_bullish_close and (not bullish or not in_zone_close):
                    continue
                if j + 1 >= n:
                    continue

                entry_o = float(open_[j + 1])
                signals.append(
                    {
                        "side": "BUY",
                        "trend": "up",
                        "idx": j,
                        "entry_idx": j + 1,
                        "signal_close": float(close[j]),
                        "entry_open": entry_o,
                        "price": entry_o,
                        "zone_low": zone_lo,
                        "zone_high": zone_hi,
                        "fib_anchor_0": hi_p,
                        "fib_anchor_1": lo_p,
                        "sl_price": lo_p,
                        "tp_price": hi_p,
                        "impulse_pct": imp_pct,
                        "level_50": hi_p - 0.5 * (hi_p - lo_p),
                        "level_618": hi_p - 0.618 * (hi_p - lo_p),
                    }
                )
                _add_setup_draw("up", i0, i1, hi_p, lo_p, zone_lo, zone_hi, j)
                used_impulses_set.add(impulse_key)
                fired = True
                break

            if fired:
                continue

        # Bearish impulse: High -> Low, pullback up into pocket -> SELL
        if t0 == "H" and t1 == "L" and i1 > i0:
            impulse_key = (i0, i1)
            if impulse_key in used_impulses_set:
                continue
            if i1 - i0 < int(min_impulse_bars):
                continue
            hi_p, lo_p = p0, p1
            imp_pct = _impulse_pct(hi_p, lo_p)
            if imp_pct < float(min_impulse_pct):
                continue

            zone_lo, zone_hi = _golden_zone_down(hi_p, lo_p, float(fib_zone_low), float(fib_zone_high))
            scan_start = i1 + int(pivot_right)
            scan_end = min(n - 2, i1 + int(max_pullback_bars))
            fired = False

            for j in range(scan_start, scan_end + 1):
                if not _bar_touches_zone(low[j], high[j], zone_lo, zone_hi):
                    continue
                bearish = close[j] < open_[j]
                in_zone_close = zone_lo <= close[j] <= zone_hi
                if require_bearish_close and (not bearish or not in_zone_close):
                    continue
                if j + 1 >= n:
                    continue

                entry_o = float(open_[j + 1])
                signals.append(
                    {
                        "side": "SELL",
                        "trend": "down",
                        "idx": j,
                        "entry_idx": j + 1,
                        "signal_close": float(close[j]),
                        "entry_open": entry_o,
                        "price": entry_o,
                        "zone_low": zone_lo,
                        "zone_high": zone_hi,
                        "fib_anchor_0": lo_p,
                        "fib_anchor_1": hi_p,
                        "sl_price": hi_p,
                        "tp_price": lo_p,
                        "impulse_pct": imp_pct,
                        "level_50": lo_p + 0.5 * (hi_p - lo_p),
                        "level_618": lo_p + 0.618 * (hi_p - lo_p),
                    }
                )
                _add_setup_draw("down", i0, i1, lo_p, hi_p, zone_lo, zone_hi, j)
                used_impulses_set.add(impulse_key)
                fired = True
                break

    raw_signal_count = len(signals)
    signals = _dedupe_nearby_signals(signals, int(min_signal_spacing_bars))

    markers = []
    for s in signals:
        entry_i = int(s["entry_idx"])
        entry_ts = pd.to_datetime(times.iloc[entry_i], utc=True)
        entry_o = float(s["entry_open"])
        if s["side"] == "BUY":
            markers.append(
                {
                    "time": int(entry_ts.timestamp()),
                    "position": "belowBar",
                    "color": "#22c55e",
                    "shape": "arrowUp",
                    "text": f"BUY\n{entry_o:.2f}",
                }
            )
        else:
            markers.append(
                {
                    "time": int(entry_ts.timestamp()),
                    "position": "aboveBar",
                    "color": "#ef5350",
                    "shape": "arrowDown",
                    "text": f"SELL\n{entry_o:.2f}",
                }
            )

    buys = sum(1 for s in signals if s["side"] == "BUY")
    sells = sum(1 for s in signals if s["side"] == "SELL")

    trade_inputs: List[Tuple[int, str, float, float, float]] = []
    for s in sorted(signals, key=lambda x: int(x["entry_idx"])):
        trade_inputs.append(
            (
                int(s["entry_idx"]),
                str(s["side"]),
                float(s["entry_open"]),
                float(s["sl_price"]),
                float(s["tp_price"]),
            )
        )

    pnl = simulate_swing_targets(
        trade_inputs,
        high,
        low,
        close,
        stake_usd=float(stake_usd),
        starting_bankroll_usd=float(starting_bankroll_usd),
    )

    return {
        "symbol": symbol.upper(),
        "timeframe": timeframe,
        "strategy": STRATEGY_ID,
        "candles": df_to_lwc(df),
        "markers": markers,
        "signals": signals,
        "fib_setups": setups_draw,
        "summary": {
            "buys": buys,
            "sells": sells,
            "total": len(signals),
            "raw_signals": raw_signal_count,
            **pnl,
        },
        "pnl": pnl,
        "params": {
            "pivot_left": int(pivot_left),
            "pivot_right": int(pivot_right),
            "min_impulse_pct": float(min_impulse_pct),
            "min_impulse_bars": int(min_impulse_bars),
            "max_pullback_bars": int(max_pullback_bars),
            "fib_zone_low": float(fib_zone_low),
            "fib_zone_high": float(fib_zone_high),
            "require_bullish_close": bool(require_bullish_close),
            "require_bearish_close": bool(require_bearish_close),
            "days_back": int(days_back),
            "exit_mode": "swing",
            "min_signal_spacing_bars": int(min_signal_spacing_bars),
            "stake_usd": float(stake_usd),
            "starting_bankroll_usd": float(starting_bankroll_usd),
        },
    }
