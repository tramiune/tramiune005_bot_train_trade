"""Decide whether a signal that the bot missed (crash, restart, outage) is still worth entering.

Pure functions only (no network, no DB) so the decision can be tested and dry-run on real data.
The rules mirror how DOGE_3M_DEGEN trades are built in TradingEngine.execute_trade.
"""
import pandas as pd

from engine.strategies.doge_3m_degen import get_all_doge_degen_signals

# Must stay equal to the DOGE_3M_DEGEN SL/TP used by execute_trade
TP_PCT = 5.0
SL_PCT = 15.0

# "Worth entering" limits
MAX_AGE_CANDLES = 60       # signal must be at most 60 closed candles old (3 hours on 3m)
MAX_DRIFT_PCT = 1.0        # price may not have moved more than 1% away from the signal entry


def find_recoverable_signal(df: pd.DataFrame,
                            max_age_candles: int = MAX_AGE_CANDLES,
                            max_drift_pct: float = MAX_DRIFT_PCT):
    """`df`: CLOSED candles only, ascending, columns timestamp(ms), open, high, low, close, volume.

    Returns (signal_dict | None, reason). A signal is recoverable only if ALL hold:
      1. it is the latest signal in the data and at most `max_age_candles` old,
      2. neither its TP nor its SL has been touched since it fired (the trade is still alive),
      3. the latest close is within `max_drift_pct` of the signal entry price.
    """
    signals = get_all_doge_degen_signals(df.copy())
    if not signals:
        return None, "no signal in the available candles"

    sig = signals[-1]
    matches = df.index[df["timestamp"] == sig["time"]]
    if len(matches) == 0:
        return None, "signal candle not found"
    pos = df.index.get_loc(matches[0])
    entry = float(sig["entry_price"])
    side = sig["side"]

    age = len(df) - 1 - pos
    if age > max_age_candles:
        return None, f"latest signal is too old ({age} candles > {max_age_candles})"

    after = df.iloc[pos + 1:]
    if side == "LONG":
        sl, tp = entry * (1 - SL_PCT / 100), entry * (1 + TP_PCT / 100)
        if (after["low"] <= sl).any():
            return None, "stop loss was already touched"
        if (after["high"] >= tp).any():
            return None, "take profit was already touched"
    else:
        sl, tp = entry * (1 + SL_PCT / 100), entry * (1 - TP_PCT / 100)
        if (after["high"] >= sl).any():
            return None, "stop loss was already touched"
        if (after["low"] <= tp).any():
            return None, "take profit was already touched"

    last_close = float(df["close"].iloc[-1])
    drift = abs(last_close - entry) / entry * 100
    if drift > max_drift_pct:
        return None, f"price drifted {drift:.2f}% from the signal entry (limit {max_drift_pct}%)"

    return {
        "side": side,
        "entry": entry,
        "time_ms": int(sig["time"]),
        "index": int(pos),
        "age_candles": int(age),
        "drift_pct": round(drift, 3),
        "sl": sl,
        "tp": tp,
    }, "ok"
