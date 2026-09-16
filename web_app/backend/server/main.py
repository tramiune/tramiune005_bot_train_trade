from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Literal, Optional
import numpy as np
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
        out.append({
            "time": int(ts.timestamp()),
            "open": float(r["open"]),
            "high": float(r["high"]),
            "low": float(r["low"]),
            "close": float(r["close"]),
        })
    return out

def _sma(s: pd.Series, n: int) -> pd.Series:
    return s.rolling(n, min_periods=n).mean()

def _ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False).mean()

def _rolling_low(s: pd.Series, n: int) -> pd.Series:
    return s.rolling(n, min_periods=n).min()

def _rolling_high(s: pd.Series, n: int) -> pd.Series:
    return s.rolling(n, min_periods=n).max()

def _atr(df: pd.DataFrame, n: int=14) -> pd.Series:
    high = df['high']
    low = df['low']
    close_prev = df['close'].shift(1)
    tr = pd.concat([high - low, (high - close_prev).abs(), (low - close_prev).abs()], axis=1).max(axis=1)
    return tr.rolling(n).mean()

def _adx(df: pd.DataFrame, n: int=14) -> pd.Series:
    up = df['high'] - df['high'].shift(1)
    down = df['low'].shift(1) - df['low']
    pos_dm = pd.Series(np.where((up > down) & (up > 0), up, 0))
    neg_dm = pd.Series(np.where((down > up) & (down > 0), down, 0))
    tr = _atr(df, 1)
    def wilder_smooth(s, n):
        res = np.zeros(len(s))
        res[0] = np.nan
        first_valid = s.first_valid_index()
        if first_valid is None: return pd.Series(res)
        res[first_valid+n-1] = s.iloc[first_valid:first_valid+n].sum()
        for i in range(first_valid+n, len(s)):
            res[i] = res[i-1] - (res[i-1]/n) + s.iloc[i]
        return pd.Series(res, index=s.index)
    atr_smooth = wilder_smooth(tr, n)
    pos_di = 100 * (wilder_smooth(pos_dm, n) / atr_smooth)
    neg_di = 100 * (wilder_smooth(neg_dm, n) / atr_smooth)
    dx = 100 * ((pos_di - neg_di).abs() / (pos_di + neg_di))
    return wilder_smooth(dx, n)

def _fetch_ohlcv_ccxt(exchange_id: str, symbol: str, timeframe: str, since: datetime, limit: int) -> pd.DataFrame:
    ex_cls = getattr(ccxt, exchange_id, None)
    if ex_cls is None:
        raise ValueError(f"unknown_exchange:{exchange_id}")
    ex = ex_cls({"enableRateLimit": True})
    ex.load_markets()
    since_ms = int(since.timestamp() * 1000)
    rows: list[list] = []
    while True:
        batch = ex.fetch_ohlcv(symbol, timeframe=timeframe, since=since_ms, limit=min(int(limit), 2000))
        if not batch: break
        rows.extend(batch)
        last_ms = int(batch[-1][0])
        next_ms = last_ms + 1
        if next_ms <= since_ms: break
        since_ms = next_ms
        if len(batch) < 2: break
        if len(rows) >= int(limit): break

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
    end_time: Optional[int] = Query(None),
):
    end_dt = datetime.now(timezone.utc) if end_time is None else datetime.fromtimestamp(int(end_time), tz=timezone.utc)
    since = end_dt - timedelta(days=int(days_back))
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
    fast: int = Query(9, ge=2, le=200),
    slow: int = Query(21, ge=5, le=500),
    rr: float = Query(1.5, ge=0.5, le=10.0),
    sl_lookback: int = Query(10, ge=2, le=200),
):
    since = datetime.now(timezone.utc) - timedelta(days=int(days_back))
    df = _fetch_ohlcv_ccxt(exchange, symbol.upper(), timeframe, since=since, limit=50000)
    if df.empty:
        return {"error": "no_data"}

    close = df["close"].astype(float)
    highs = df["high"].astype(float)
    lows = df["low"].astype(float)

    s_fast = _sma(close, int(fast))
    s_slow = _sma(close, int(slow))
    e200 = _ema(close, 200)
    
    df['ATR'] = _atr(df, 14)
    df['ADX'] = _adx(df, 14)

    cross_up = (s_fast > s_slow) & (s_fast.shift(1) <= s_slow.shift(1))
    cross_dn = (s_fast < s_slow) & (s_fast.shift(1) >= s_slow.shift(1))

    sl_low_base = _rolling_low(lows, int(sl_lookback)).shift(1)
    sl_high_base = _rolling_high(highs, int(sl_lookback)).shift(1)

    trades: list[dict] = []
    i = 0
    min_i = max(int(fast), int(slow), int(sl_lookback), 200, 28) + 2
    while i < len(df):
        if i < min_i:
            i += 1
            continue

        entry = float(close.iloc[i])
        ts_entry = pd.to_datetime(df["timestamp"].iloc[i], utc=True)
        
        adx = float(df["ADX"].iloc[i]) if pd.notna(df["ADX"].iloc[i]) else 0
        atr = float(df["ATR"].iloc[i]) if pd.notna(df["ATR"].iloc[i]) else 0
        ema200_val = float(e200.iloc[i])

        side: str | None = None
        sl: float | None = None
        
        # Filtering conditions
        trend_up = entry > ema200_val
        trend_dn = entry < ema200_val
        
        if bool(cross_up.iloc[i]) and adx > 20 and trend_up:
            side = "LONG"
            b = float(sl_low_base.iloc[i]) if pd.notna(sl_low_base.iloc[i]) else None
            if b is not None:
                sl = b - (atr * 1.5)
        elif bool(cross_dn.iloc[i]) and adx > 20 and trend_dn:
            side = "SHORT"
            b = float(sl_high_base.iloc[i]) if pd.notna(sl_high_base.iloc[i]) else None
            if b is not None:
                sl = b + (atr * 1.5)

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

@app.post("/api/backtest/smc")
def backtest_smc(
    symbol: str = Query(...),
    timeframe: Timeframe = Query("1h"),
    days_back: int = Query(180, ge=10, le=3650),
    exchange: str = Query("binance"),
    rr: float = Query(2.0, ge=0.5, le=10.0),
):
    since = datetime.now(timezone.utc) - timedelta(days=int(days_back))
    df = _fetch_ohlcv_ccxt(exchange, symbol.upper(), timeframe, since=since, limit=50000)
    if df.empty:
        return {"error": "no_data"}

    close = df["close"].astype(float)
    highs = df["high"].astype(float)
    lows = df["low"].astype(float)
    vols = df["volume"].astype(float)

    e200 = _ema(close, 200)
    v20 = _sma(vols, 20)
    sma20 = _sma(close, 20)
    std20 = close.rolling(20).std()
    lower_band = sma20 - 2 * std20

    trades = []
    i = max(200, 20) + 2
    
    while i < len(df) - 1:
        c = float(close.iloc[i])
        h = float(highs.iloc[i])
        l = float(lows.iloc[i])
        v = float(vols.iloc[i])
        v_ma = float(v20.iloc[i]) if pd.notna(v20.iloc[i]) else 0
        e2 = float(e200.iloc[i])
        lb = float(lower_band.iloc[i]) if pd.notna(lower_band.iloc[i]) else 0
        ts_entry = pd.to_datetime(df["timestamp"].iloc[i], utc=True)

        side = None
        sl = None
        
        # Smart Money Dip Buying (Bullish)
        if c > e2 and l < lb and (1.5 * v_ma < v < 2.0 * v_ma) and ts_entry.dayofweek != 0:
            candle_range = h - l
            if candle_range > 0:
                close_percent = (c - l) / candle_range
                # Fetch filters
                prev_5_drop = 0
                if i >= 5:
                    prev_5_drop = (float(close.iloc[i-5]) - c) / c * 100
                dist_to_e200 = (c - e2) / e2 * 100
                
                # Close in top 50%, NOT falling knife (<0.6% drop), NOT over-extended (<2.0% dist)
                if close_percent > 0.5 and prev_5_drop < 0.6 and dist_to_e200 < 2.0:
                    side = "LONG"
                    sl = l - (candle_range * 0.2)
                    
        if side:
            risk = abs(c - sl)
            if risk > 0:
                tp = c + float(rr) * risk
                j = i + 1
                exit_idx = None
                result = None
                exit_price = None
                
                while j < len(df):
                    hi = float(highs.iloc[j])
                    lo = float(lows.iloc[j])
                    if lo <= sl: exit_idx, exit_price, result = j, float(sl), "LOSS"; break
                    if hi >= tp: exit_idx, exit_price, result = j, float(tp), "WIN"; break
                    j += 1
                    
                if exit_idx is not None:
                    r_multiple = (abs(exit_price - c) / risk) * (1 if result == "WIN" else -1)
                    trades.append({
                        "side": side,
                        "entry_idx": i,
                        "entry_ts": ts_entry,
                        "r_multiple": float(r_multiple),
                        "result": result,
                    })
                    i = exit_idx
        i += 1

    markers = []
    for t in trades:
        ts = pd.to_datetime(t["entry_ts"], utc=True)
        markers.append({
            "time": int(ts.timestamp()),
            "position": "belowBar",
            "color": "#26a69a",
            "shape": "arrowUp",
            "text": f"SMC BUY R={t['r_multiple']:+.2f}",
        })

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


@app.get("/api/backtest/eth_squeeze")
def backtest_eth_squeeze(symbol: str = "ETH/USDT", timeframe: str = "1h", limit: int = 50000, rr: float = 5.0):
    since = datetime.now(timezone.utc) - timedelta(days=limit)
    df = _fetch_ohlcv_ccxt("binance", symbol, timeframe, since=since, limit=100000)
    if df.empty:
        return {"data": [], "markers": [], "metrics": {}}

    close = df["close"].astype(float)
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    vol = df["volume"].astype(float)

    sma20 = _sma(close, 20)
    std20 = close.rolling(20).std()
    bb_upper = sma20 + 2 * std20
    bb_lower = sma20 - 2 * std20

    ema20 = _ema(close, 20)
    atr20 = _atr(df, 20)
    kc_upper = ema20 + 1.5 * atr20
    kc_lower = ema20 - 1.5 * atr20

    atr14 = _atr(df, 14)
    v20 = _sma(vol, 20)
    e200 = _ema(close, 200)

    is_squeeze = (bb_upper < kc_upper) & (bb_lower > kc_lower)
    
    squeeze_durations = []
    current_duration = 0
    for val in is_squeeze:
        if val:
            current_duration += 1
        else:
            current_duration = 0
        squeeze_durations.append(current_duration)
    df['squeeze_duration'] = squeeze_durations

    markers = []
    i = 205
    wins = 0
    losses = 0

    while i < len(df) - 1:
        c = float(close.iloc[i])
        h = float(high.iloc[i])
        l = float(low.iloc[i])
        v = float(vol.iloc[i])
        v_ma = float(v20.iloc[i]) if pd.notna(v20.iloc[i]) else 0
        b_up = float(bb_upper.iloc[i])
        e2 = float(e200.iloc[i])
        at = float(atr14.iloc[i]) if pd.notna(atr14.iloc[i]) else 0
        dt = pd.to_datetime(df["timestamp"].iloc[i], utc=True)
        ts_ms = int(dt.timestamp() * 1000)

        recent_squeeze = is_squeeze.iloc[i-3:i+1].any()
        max_duration = df['squeeze_duration'].iloc[i-10:i+1].max()
        vol_mult = v / v_ma if v_ma > 0 else 0
        dist_e200 = (c - e2) / e2 * 100
        candle_size_pct = (h - l) / c * 100

        if recent_squeeze and c > b_up and (2.0 < vol_mult < 3.0) and c > e2 and dt.dayofweek != 0 and dist_e200 >= 1.0 and max_duration < 6 and candle_size_pct < 2.0:
            entry = c
            sl = l
            if (entry - sl) < 0.3 * at:
                sl = entry - 0.5 * at

            risk = entry - sl
            if risk > 0:
                tp = entry + rr * risk
                j = i + 1
                exit_idx = None
                result = None
                exit_price = 0

                while j < len(df):
                    hi = float(high.iloc[j])
                    lo = float(low.iloc[j])
                    if lo <= sl: 
                        exit_idx, result, exit_price = j, "LOSS", sl
                        break
                    if hi >= tp: 
                        exit_idx, result, exit_price = j, "WIN", tp
                        break
                    j += 1

                if exit_idx is not None:
                    exit_ts = int(pd.to_datetime(df["timestamp"].iloc[exit_idx], utc=True).timestamp() * 1000)
                    markers.append({
                        "time": ts_ms,
                        "position": "belowBar",
                        "color": "#2196F3",
                        "shape": "arrowUp",
                        "text": f"BUY @ {entry:.2f}"
                    })
                    if result == "WIN":
                        wins += 1
                        markers.append({
                            "time": exit_ts,
                            "position": "aboveBar",
                            "color": "#4CAF50",
                            "shape": "arrowDown",
                            "text": f"TP (+{rr}R) @ {exit_price:.2f}"
                        })
                    else:
                        losses += 1
                        markers.append({
                            "time": exit_ts,
                            "position": "aboveBar",
                            "color": "#F44336",
                            "shape": "arrowDown",
                            "text": f"SL (-1R) @ {exit_price:.2f}"
                        })
                    i = exit_idx
        i += 1

    chart_data = []
    for idx, row in df.iterrows():
        chart_data.append({
            "time": int(pd.to_datetime(row["timestamp"], utc=True).timestamp() * 1000),
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"])
        })

    total = wins + losses
    winrate = round(wins / total * 100, 2) if total > 0 else 0
    profit_r = round((wins * rr) - (losses * 1.0), 2)

    return {
        "data": chart_data,
        "markers": markers,
        "metrics": {
            "total_trades": total,
            "wins": wins,
            "losses": losses,
            "winrate": winrate,
            "profit_r": profit_r
        }
    }

@app.get("/api/backtest/sol_retest")
def backtest_sol_retest(symbol: str = "SOL/USDT", timeframe: str = "1h", limit: int = 50000, rr: float = 15.0):
    since = datetime.now(timezone.utc) - timedelta(days=limit)
    sol = _fetch_ohlcv_ccxt("binance", symbol, timeframe, since=since, limit=100000)
    btc = _fetch_ohlcv_ccxt("binance", "BTC/USDT", timeframe, since=since, limit=100000)
    
    if sol.empty or btc.empty:
        return {"data": [], "markers": [], "metrics": {}}

    btc = btc[["timestamp", "close"]].rename(columns={"close": "btc_close"})
    df = pd.merge(sol, btc, on="timestamp", how="left")
    
    df["e200"] = _ema(df["close"], 200)
    df["e20"] = _ema(df["close"], 20)
    df["atr14"] = _atr(df, 14)
    df["v20"] = _sma(df["volume"], 20)
    df["btc_e200"] = _ema(df["btc_close"], 200)
    
    markers = []
    i = 205
    last_bullish_cross_idx = 0
    wins = 0
    losses = 0

    while i < len(df) - 1:
        c = float(df["close"].iloc[i])
        h = float(df["high"].iloc[i])
        l = float(df["low"].iloc[i])
        v = float(df["volume"].iloc[i])
        
        e200_val = float(df["e200"].iloc[i]) if pd.notna(df["e200"].iloc[i]) else 0
        e20_val = float(df["e20"].iloc[i]) if pd.notna(df["e20"].iloc[i]) else 0
        prev_e20 = float(df["e20"].iloc[i-1]) if pd.notna(df["e20"].iloc[i-1]) else 0
        prev_e200 = float(df["e200"].iloc[i-1]) if pd.notna(df["e200"].iloc[i-1]) else 0
        at = float(df["atr14"].iloc[i]) if pd.notna(df["atr14"].iloc[i]) else 0
        v_ma = float(df["v20"].iloc[i]) if pd.notna(df["v20"].iloc[i]) else 0
        
        btc_c = float(df["btc_close"].iloc[i]) if pd.notna(df["btc_close"].iloc[i]) else 0
        btc_e200_val = float(df["btc_e200"].iloc[i]) if pd.notna(df["btc_e200"].iloc[i]) else 0
        
        if prev_e20 <= prev_e200 and e20_val > e200_val:
            last_bullish_cross_idx = i
            
        candle_range = h - l
        close_pct = (c - l) / candle_range if candle_range > 0 else 0
        
        dt = pd.to_datetime(df["timestamp"].iloc[i], utc=True)
        ts_ms = int(dt.timestamp() * 1000)
        day = dt.dayofweek
        
        is_uptrend = e20_val > e200_val
        candles_since_cross = i - last_bullish_cross_idx
        is_proper_speed = 20 <= candles_since_cross < 150
        is_strong_rejection = close_pct > 0.6
        has_volume = (v / v_ma) > 1.2 if v_ma > 0 else False
        is_touching = l <= e200_val and c > e200_val
        btc_bullish = btc_c > btc_e200_val
        is_midweek = day in [1, 2, 3] # Tue, Wed, Thu
        
        if is_uptrend and is_proper_speed and is_touching and is_strong_rejection and has_volume and btc_bullish and is_midweek:
            entry = c
            sl = entry - 1.5 * at
            
            risk = entry - sl
            if risk > 0:
                tp = entry + float(rr) * risk
                
                j = i + 1
                exit_idx = None
                result = None
                exit_price = 0
                
                while j < len(df):
                    hi = float(df["high"].iloc[j])
                    lo = float(df["low"].iloc[j])
                    if lo <= sl: exit_idx, result, exit_price = j, "LOSS", sl; break
                    if hi >= tp: exit_idx, result, exit_price = j, "WIN", tp; break
                    j += 1
                    
                if exit_idx is not None:
                    exit_ts = int(pd.to_datetime(df["timestamp"].iloc[exit_idx], utc=True).timestamp() * 1000)
                    markers.append({
                        "time": ts_ms,
                        "position": "belowBar",
                        "color": "#9C27B0",
                        "shape": "arrowUp",
                        "text": f"RETEST BUY @ {entry:.2f}"
                    })
                    if result == "WIN":
                        wins += 1
                        markers.append({
                            "time": exit_ts,
                            "position": "aboveBar",
                            "color": "#4CAF50",
                            "shape": "arrowDown",
                            "text": f"TP (+{rr}R) @ {exit_price:.2f}"
                        })
                    else:
                        losses += 1
                        markers.append({
                            "time": exit_ts,
                            "position": "aboveBar",
                            "color": "#F44336",
                            "shape": "arrowDown",
                            "text": f"SL (-1R) @ {exit_price:.2f}"
                        })
                    i = exit_idx
                    continue
        i += 1

    chart_data = []
    for idx, row in df.iterrows():
        chart_data.append({
            "time": int(pd.to_datetime(row["timestamp"], utc=True).timestamp() * 1000),
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"])
        })

    total = wins + losses
    winrate = round(wins / total * 100, 2) if total > 0 else 0
    profit_r = round((wins * rr) - (losses * 1.0), 2)

    return {
        "data": chart_data,
        "markers": markers,
        "metrics": {
            "total_trades": total,
            "wins": wins,
            "losses": losses,
            "winrate": winrate,
            "profit_r": profit_r
        }
    }
