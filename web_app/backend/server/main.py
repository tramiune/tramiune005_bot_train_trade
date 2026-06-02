from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal

import pandas as pd
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

# Reuse existing bot modules (Python path trick)
import sys

ROOT = Path(__file__).resolve().parents[3]  # repo root
BOT_PKG_ROOT = ROOT / "trading_bot"  # contains "app/" package
if str(BOT_PKG_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_PKG_ROOT))

from app.backtest.backtester import Backtester  # noqa: E402
from app.data.ohlcv_provider import get_provider  # noqa: E402

app = FastAPI(title="Trading Web Backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Timeframe = Literal["1m", "5m", "15m", "1h", "4h", "1d"]


def _df_to_lwc(df: pd.DataFrame) -> list[dict]:
    out: list[dict] = []
    for _, r in df.iterrows():
        ts: pd.Timestamp = pd.to_datetime(r["timestamp"], utc=True)
        out.append(
            {
                "time": int(ts.timestamp()),
                "open": float(r["open"]),
                "high": float(r["high"]),
                "low": float(r["low"]),
                "close": float(r["close"]),
            }
        )
    return out


@app.get("/api/symbols")
def symbols():
    return {
        "symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT"],
        "timeframes": ["1m", "5m", "15m", "1h", "4h", "1d"],
    }


@app.get("/api/ohlcv")
def ohlcv(
    symbol: str = Query(...),
    timeframe: Timeframe = Query("15m"),
    days_back: int = Query(30, ge=1, le=3650),
    provider: str = Query("ccxt"),
    exchange: str = Query("binance"),
    limit: int = Query(2000, ge=100, le=50000),
):
    p = get_provider(provider, exchange_id=exchange) if provider == "ccxt" else get_provider(provider)
    since = datetime.now(timezone.utc) - timedelta(days=int(days_back))
    df = p.fetch_ohlcv(symbol.upper(), timeframe, limit=int(limit), since=since)
    return {"symbol": symbol.upper(), "timeframe": timeframe, "candles": _df_to_lwc(df)}


@app.post("/api/backtest/sma_cross")
def backtest_sma_cross(
    symbol: str = Query(...),
    timeframe: Timeframe = Query("15m"),
    days_back: int = Query(180, ge=10, le=3650),
    provider: str = Query("ccxt"),
    exchange: str = Query("binance"),
    fast: int = Query(20, ge=2, le=200),
    slow: int = Query(50, ge=5, le=500),
    rr: float = Query(2.0, ge=1.0, le=10.0),
    sl_lookback: int = Query(10, ge=2, le=200),
    tp_lookback: int = Query(50, ge=5, le=500),
):
    from app.rules.indicators import rolling_high, rolling_low, sma  # noqa: E402
    from app.rules.base import TradeSignal  # noqa: E402

    p = get_provider(provider, exchange_id=exchange) if provider == "ccxt" else get_provider(provider)
    since = datetime.now(timezone.utc) - timedelta(days=int(days_back))
    df = p.fetch_ohlcv(symbol.upper(), timeframe, limit=50000, since=since)
    if df.empty:
        return {"error": "no_data"}

    close = df["close"].astype(float)
    s_fast = sma(close, int(fast))
    s_slow = sma(close, int(slow))

    cross_up = (s_fast > s_slow) & (s_fast.shift(1) <= s_slow.shift(1))
    cross_dn = (s_fast < s_slow) & (s_fast.shift(1) >= s_slow.shift(1))

    sl_low = rolling_low(df["low"].astype(float), int(sl_lookback)).shift(1)
    sl_high = rolling_high(df["high"].astype(float), int(sl_lookback)).shift(1)
    tp_high = rolling_high(df["high"].astype(float), int(tp_lookback)).shift(1)
    tp_low = rolling_low(df["low"].astype(float), int(tp_lookback)).shift(1)

    signals: list[TradeSignal] = []
    for i in range(len(df)):
        if i < max(fast, slow, sl_lookback, tp_lookback) + 2:
            continue
        entry = float(close.iloc[i])
        if bool(cross_up.iloc[i]):
            sl = float(sl_low.iloc[i]) if pd.notna(sl_low.iloc[i]) else None
            tp = float(tp_high.iloc[i]) if pd.notna(tp_high.iloc[i]) else None
            if sl is None or tp is None:
                continue
            risk = abs(entry - sl)
            reward = abs(tp - entry)
            if risk <= 0 or reward / risk < float(rr):
                continue
            signals.append(
                TradeSignal(
                    side="LONG",
                    entry_idx=i,
                    entry_price=entry,
                    stop_loss=float(sl),
                    take_profit=float(tp),
                    rule_name=f"sma_cross({fast},{slow})",
                    meta={},
                )
            )
        elif bool(cross_dn.iloc[i]):
            sl = float(sl_high.iloc[i]) if pd.notna(sl_high.iloc[i]) else None
            tp = float(tp_low.iloc[i]) if pd.notna(tp_low.iloc[i]) else None
            if sl is None or tp is None:
                continue
            risk = abs(entry - sl)
            reward = abs(entry - tp)
            if risk <= 0 or reward / risk < float(rr):
                continue
            signals.append(
                TradeSignal(
                    side="SHORT",
                    entry_idx=i,
                    entry_price=entry,
                    stop_loss=float(sl),
                    take_profit=float(tp),
                    rule_name=f"sma_cross({fast},{slow})",
                    meta={},
                )
            )

    bt = Backtester(max_hold_bars=None)
    trades = bt.run(df, signals)

    markers = []
    for t in trades:
        ts = pd.to_datetime(df["timestamp"].iloc[t.entry_idx], utc=True)
        markers.append(
            {
                "time": int(ts.timestamp()),
                "position": "belowBar" if t.side == "LONG" else "aboveBar",
                "color": "#26a69a" if t.side == "LONG" else "#ef5350",
                "shape": "arrowUp" if t.side == "LONG" else "arrowDown",
                "text": f"{t.side} R={t.r_multiple:+.2f}",
            }
        )

    return {
        "symbol": symbol.upper(),
        "timeframe": timeframe,
        "candles": _df_to_lwc(df),
        "markers": markers,
        "summary": {
            "trades": len(trades),
            "avg_r": (sum(x.r_multiple for x in trades) / len(trades)) if trades else 0.0,
            "winrate": (100.0 * sum(1 for x in trades if x.result == "WIN") / len(trades)) if trades else 0.0,
        },
    }

