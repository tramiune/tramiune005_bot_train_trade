from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Query

from .backtest import run_fib_golden_pocket_backtest

router = APIRouter(tags=["fib_golden_pocket"])

Timeframe = Literal["1m", "5m", "15m", "1h", "4h", "1d"]


@router.post("/api/backtest/fib_golden_pocket")
def backtest_fib_golden_pocket(
    symbol: str = Query(...),
    timeframe: Timeframe = Query("15m"),
    days_back: int = Query(180, ge=30, le=3650),
    exchange: str = Query("binance"),
    limit: int = Query(50000, ge=1000, le=50000),
    pivot_left: int = Query(5, ge=1, le=20),
    pivot_right: int = Query(5, ge=1, le=20),
    min_impulse_pct: float = Query(1.5, ge=0.2, le=50.0),
    min_impulse_bars: int = Query(8, ge=3, le=200),
    max_pullback_bars: int = Query(120, ge=10, le=500),
    fib_zone_low: float = Query(0.5, ge=0.1, le=0.9),
    fib_zone_high: float = Query(0.618, ge=0.2, le=0.95),
    require_bullish_close: bool = Query(True),
    require_bearish_close: bool = Query(True),
    min_signal_spacing_bars: int = Query(24, ge=0, le=500),
    stake_usd: float = Query(100.0, ge=1, le=100000),
    starting_bankroll_usd: float = Query(1000.0, ge=1, le=10_000_000),
):
    return run_fib_golden_pocket_backtest(
        symbol=symbol,
        timeframe=timeframe,
        days_back=days_back,
        exchange=exchange,
        limit=limit,
        pivot_left=pivot_left,
        pivot_right=pivot_right,
        min_impulse_pct=min_impulse_pct,
        min_impulse_bars=min_impulse_bars,
        max_pullback_bars=max_pullback_bars,
        fib_zone_low=fib_zone_low,
        fib_zone_high=fib_zone_high,
        require_bullish_close=require_bullish_close,
        require_bearish_close=require_bearish_close,
        min_signal_spacing_bars=min_signal_spacing_bars,
        stake_usd=stake_usd,
        starting_bankroll_usd=starting_bankroll_usd,
    )
