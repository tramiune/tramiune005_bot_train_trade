from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Literal, Optional

import ccxt
import pandas as pd
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

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


def _sma(s: pd.Series, n: int) -> pd.Series:
    return s.rolling(n, min_periods=n).mean()


def _rolling_low(s: pd.Series, n: int) -> pd.Series:
    return s.rolling(n, min_periods=n).min()


def _rolling_high(s: pd.Series, n: int) -> pd.Series:
    return s.rolling(n, min_periods=n).max()


def _fetch_ohlcv_ccxt(exchange_id: str, symbol: str, timeframe: str, since: datetime, limit: int) -> pd.DataFrame:
    ex_cls = getattr(ccxt, exchange_id, None)
    if ex_cls is None:
        raise ValueError(f"unknown_exchange:{exchange_id}")
    ex = ex_cls({"enableRateLimit": True})
    ex.load_markets()
    since_ms = int(since.timestamp() * 1000)

    rows: list[list] = []
    # ccxt may cap limit per request; loop until we cover the range
    while True:
        batch = ex.fetch_ohlcv(symbol, timeframe=timeframe, since=since_ms, limit=min(int(limit), 2000))
        if not batch:
            break
        rows.extend(batch)
        last_ms = int(batch[-1][0])
        # advance 1ms to avoid duplicates
        next_ms = last_ms + 1
        if next_ms <= since_ms:
            break
        since_ms = next_ms
        if len(batch) < 2:
            break
        if len(rows) >= int(limit):
            break

    if not rows:
        return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])

    df = pd.DataFrame(rows, columns=["timestamp_ms", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp_ms"], unit="ms", utc=True)
    df = df.drop(columns=["timestamp_ms"])
    df = df.sort_values("timestamp").reset_index(drop=True)
    return df


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
    exchange: str = Query("binance"),
    limit: int = Query(2000, ge=100, le=50000),
    end_time: Optional[int] = Query(
        None, description="Unix seconds (UTC). If set, return candles strictly before this time."
    ),
):
    end_dt = datetime.now(timezone.utc) if end_time is None else datetime.fromtimestamp(int(end_time), tz=timezone.utc)
    since = end_dt - timedelta(days=int(days_back))
    # Fetch a wider window then slice to the requested end_time & limit.
    df = _fetch_ohlcv_ccxt(exchange, symbol.upper(), timeframe, since=since, limit=int(limit) * 3)
    if end_time is not None and not df.empty:
        df = df[df["timestamp"] < end_dt]
    if not df.empty:
        df = df.tail(int(limit)).reset_index(drop=True)
    return {"symbol": symbol.upper(), "timeframe": timeframe, "candles": _df_to_lwc(df)}


@app.post("/api/backtest/sma_cross")
def backtest_sma_cross(
    symbol: str = Query(...),
    timeframe: Timeframe = Query("15m"),
    days_back: int = Query(180, ge=10, le=3650),
    exchange: str = Query("binance"),
    fast: int = Query(20, ge=2, le=200),
    slow: int = Query(50, ge=5, le=500),
    rr: float = Query(2.0, ge=1.0, le=10.0),
    sl_lookback: int = Query(10, ge=2, le=200),
):
    since = datetime.now(timezone.utc) - timedelta(days=int(days_back))
    df = _fetch_ohlcv_ccxt(exchange, symbol.upper(), timeframe, since=since, limit=50000)
    if df.empty:
        return {"error": "no_data"}

    close = df["close"].astype(float)
    s_fast = _sma(close, int(fast))
    s_slow = _sma(close, int(slow))

    cross_up = (s_fast > s_slow) & (s_fast.shift(1) <= s_slow.shift(1))
    cross_dn = (s_fast < s_slow) & (s_fast.shift(1) >= s_slow.shift(1))

    lows = df["low"].astype(float)
    highs = df["high"].astype(float)
    sl_low = _rolling_low(lows, int(sl_lookback)).shift(1)
    sl_high = _rolling_high(highs, int(sl_lookback)).shift(1)

    trades: list[dict] = []
    i = 0
    min_i = max(int(fast), int(slow), int(sl_lookback)) + 2
    while i < len(df):
        if i < min_i:
            i += 1
            continue

        entry = float(close.iloc[i])
        ts_entry = pd.to_datetime(df["timestamp"].iloc[i], utc=True)

        side: str | None = None
        sl: float | None = None
        if bool(cross_up.iloc[i]):
            side = "LONG"
            sl = float(sl_low.iloc[i]) if pd.notna(sl_low.iloc[i]) else None
        elif bool(cross_dn.iloc[i]):
            side = "SHORT"
            sl = float(sl_high.iloc[i]) if pd.notna(sl_high.iloc[i]) else None

        if side is None or sl is None:
            i += 1
            continue

        risk = abs(entry - sl)
        if risk <= 0:
            i += 1
            continue

        tp = entry + float(rr) * risk if side == "LONG" else entry - float(rr) * risk

        exit_idx: int | None = None
        result: str | None = None
        exit_price: float | None = None

        j = i + 1
        while j < len(df):
            hi = float(highs.iloc[j])
            lo = float(lows.iloc[j])
            if side == "LONG":
                sl_hit = lo <= sl
                tp_hit = hi >= tp
                if sl_hit and tp_hit:
                    # ambiguous; assume worst-case for safety
                    exit_idx, exit_price, result = j, float(sl), "LOSS"
                    break
                if sl_hit:
                    exit_idx, exit_price, result = j, float(sl), "LOSS"
                    break
                if tp_hit:
                    exit_idx, exit_price, result = j, float(tp), "WIN"
                    break
            else:
                sl_hit = hi >= sl
                tp_hit = lo <= tp
                if sl_hit and tp_hit:
                    exit_idx, exit_price, result = j, float(sl), "LOSS"
                    break
                if sl_hit:
                    exit_idx, exit_price, result = j, float(sl), "LOSS"
                    break
                if tp_hit:
                    exit_idx, exit_price, result = j, float(tp), "WIN"
                    break
            j += 1

        if exit_idx is None:
            i += 1
            continue

        r_multiple = (abs(exit_price - entry) / risk) * (1 if result == "WIN" else -1)
        trades.append(
            {
                "side": side,
                "entry_idx": i,
                "entry_ts": ts_entry,
                "r_multiple": float(r_multiple),
                "result": result,
            }
        )

        # move forward to avoid overlapping trades
        i = exit_idx + 1

    markers: list[dict] = []
    for t in trades:
        ts = pd.to_datetime(t["entry_ts"], utc=True)
        markers.append(
            {
                "time": int(ts.timestamp()),
                "position": "belowBar" if t["side"] == "LONG" else "aboveBar",
                "color": "#26a69a" if t["side"] == "LONG" else "#ef5350",
                "shape": "arrowUp" if t["side"] == "LONG" else "arrowDown",
                "text": f"{t['side']} R={t['r_multiple']:+.2f}",
            }
        )

    return {
        "symbol": symbol.upper(),
        "timeframe": timeframe,
        "candles": _df_to_lwc(df),
        "markers": markers,
        "summary": {
            "trades": len(trades),
            "avg_r": (sum(float(x["r_multiple"]) for x in trades) / len(trades)) if trades else 0.0,
            "winrate": (100.0 * sum(1 for x in trades if x["result"] == "WIN") / len(trades)) if trades else 0.0,
        },
    }

