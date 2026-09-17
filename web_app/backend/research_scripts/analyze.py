from datetime import datetime, timedelta, timezone
import pandas as pd
from server.main import _fetch_ohlcv_ccxt, _sma, _rolling_low, _rolling_high

def analyze():
    print("Fetching data...")
    symbol = "BTC/USDT"
    timeframe = "15m"
    days_back = 30
    since = datetime.now(timezone.utc) - timedelta(days=days_back)
    
    df = _fetch_ohlcv_ccxt("binance", symbol, timeframe, since=since, limit=50000)
    print(f"Fetched {len(df)} rows.")

    fast = 20
    slow = 50
    sl_lookback = 10
    rr = 2.0

    close = df["close"].astype(float)
    s_fast = _sma(close, fast)
    s_slow = _sma(close, slow)

    cross_up = (s_fast > s_slow) & (s_fast.shift(1) <= s_slow.shift(1))
    cross_dn = (s_fast < s_slow) & (s_fast.shift(1) >= s_slow.shift(1))

    lows = df["low"].astype(float)
    highs = df["high"].astype(float)
    sl_low = _rolling_low(lows, sl_lookback).shift(1)
    sl_high = _rolling_high(highs, sl_lookback).shift(1)

    trades = []
    i = 0
    min_i = max(fast, slow, sl_lookback) + 2
    
    while i < len(df):
        if i < min_i:
            i += 1
            continue

        entry = float(close.iloc[i])
        ts_entry = df["timestamp"].iloc[i]

        side = None
        sl = None
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

        tp = entry + rr * risk if side == "LONG" else entry - rr * risk

        exit_idx = None
        result = None
        exit_price = None

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

        # Extract context: 20 candles before entry
        context_df = df.iloc[i-20:i]
        price_change_pct = (context_df["close"].iloc[-1] - context_df["close"].iloc[0]) / context_df["close"].iloc[0] * 100
        atr_approx = context_df["high"].max() - context_df["low"].min()

        trades.append({
            "side": side,
            "entry_ts": ts_entry,
            "entry_price": entry,
            "sl": sl,
            "tp": tp,
            "exit_ts": df["timestamp"].iloc[exit_idx],
            "result": result,
            "context_trend_pct": price_change_pct,
            "context_atr_approx": atr_approx
        })

        i = exit_idx + 1

    wins = [t for t in trades if t["result"] == "WIN"]
    losses = [t for t in trades if t["result"] == "LOSS"]

    print(f"\n--- BACKTEST SUMMARY ---")
    print(f"Total Trades: {len(trades)}")
    print(f"Wins: {len(wins)}, Losses: {len(losses)}")
    winrate = len(wins) / len(trades) * 100 if trades else 0
    print(f"Winrate: {winrate:.2f}%\n")

    print(f"--- ANALYZING RECENT LOSSES ---")
    for t in losses[-5:]:
        print(f"[{t['entry_ts']}] {t['side']} at {t['entry_price']:.2f} | SL: {t['sl']:.2f} | TP: {t['tp']:.2f}")
        print(f"  -> Result: LOSS at {t['exit_ts']}")
        print(f"  -> Context (20 bars before): Trend = {t['context_trend_pct']:.2f}%, Range = {t['context_atr_approx']:.2f}")
        print("-" * 40)

if __name__ == "__main__":
    analyze()
