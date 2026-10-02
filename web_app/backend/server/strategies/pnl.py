from __future__ import annotations

from typing import Dict, List, Tuple

import numpy as np


def simulate_sl_tp(
    signals: List[Tuple[int, str, float]],
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    sl_pct: float,
    tp_pct: float,
    stake_usd: float = 100.0,
    starting_bankroll_usd: float = 1000.0,
) -> Dict[str, float]:
    """Fixed % SL/TP from entry; one position at a time; fixed $ stake per trade."""
    empty = {
        "trades": 0,
        "wins": 0,
        "winrate": 0.0,
        "total_pnl_pct": 0.0,
        "avg_pnl_pct": 0.0,
        "profit_factor": 0.0,
        "stake_usd": float(stake_usd),
        "starting_bankroll_usd": float(starting_bankroll_usd),
        "total_staked_usd": 0.0,
        "total_returned_usd": 0.0,
        "net_pnl_usd": 0.0,
        "ending_bankroll_usd": float(starting_bankroll_usd),
        "return_on_bankroll_pct": 0.0,
        "return_on_staked_pct": 0.0,
        "sl_pct": float(sl_pct),
        "tp_pct": float(tp_pct),
    }
    if not signals:
        return empty

    n = len(close)
    sl = sl_pct / 100.0
    tp = tp_pct / 100.0
    pos_end = -1
    pnls: List[float] = []

    for entry_i, side, entry in signals:
        if entry_i <= pos_end or entry_i >= n:
            continue
        if side == "BUY":
            sl_price = entry * (1.0 - sl)
            tp_price = entry * (1.0 + tp)
        else:
            sl_price = entry * (1.0 + sl)
            tp_price = entry * (1.0 - tp)

        exit_i = n - 1
        pnl = 0.0
        hit = False
        for j in range(entry_i, n):
            h, l = high[j], low[j]
            if side == "BUY":
                if l <= sl_price:
                    pnl = -sl_pct
                    exit_i = j
                    hit = True
                    break
                if h >= tp_price:
                    pnl = tp_pct
                    exit_i = j
                    hit = True
                    break
            else:
                if h >= sl_price:
                    pnl = -sl_pct
                    exit_i = j
                    hit = True
                    break
                if l <= tp_price:
                    pnl = tp_pct
                    exit_i = j
                    hit = True
                    break
        if not hit:
            exit_price = float(close[n - 1])
            if side == "BUY":
                pnl = (exit_price - entry) / entry * 100.0
            else:
                pnl = (entry - exit_price) / entry * 100.0
            exit_i = n - 1

        pnls.append(pnl)
        pos_end = exit_i

    wins = sum(1 for p in pnls if p > 0)
    losses = sum(-p for p in pnls if p < 0)
    gains = sum(p for p in pnls if p > 0)
    total_pct = sum(pnls)
    pf = (gains / losses) if losses > 0 else (gains if gains > 0 else 0.0)

    stake = float(stake_usd)
    bankroll0 = float(starting_bankroll_usd)
    pnls_usd = [stake * (p / 100.0) for p in pnls]
    trade_n = len(pnls_usd)
    total_staked = stake * trade_n
    net_usd = float(sum(pnls_usd))
    total_returned = total_staked + net_usd
    ending = bankroll0 + net_usd

    return {
        "trades": trade_n,
        "wins": wins,
        "winrate": 100.0 * wins / trade_n if trade_n else 0.0,
        "total_pnl_pct": total_pct,
        "avg_pnl_pct": total_pct / trade_n if trade_n else 0.0,
        "profit_factor": pf,
        "stake_usd": stake,
        "starting_bankroll_usd": bankroll0,
        "total_staked_usd": round(total_staked, 2),
        "total_returned_usd": round(total_returned, 2),
        "net_pnl_usd": round(net_usd, 2),
        "ending_bankroll_usd": round(ending, 2),
        "return_on_bankroll_pct": round((net_usd / bankroll0 * 100.0) if bankroll0 > 0 else 0.0, 2),
        "return_on_staked_pct": round((net_usd / total_staked * 100.0) if total_staked > 0 else 0.0, 2),
        "sl_pct": float(sl_pct),
        "tp_pct": float(tp_pct),
        "exit_mode": "pct",
    }


def simulate_swing_targets(
    trades: List[Tuple[int, str, float, float, float]],
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    stake_usd: float = 100.0,
    starting_bankroll_usd: float = 1000.0,
) -> Dict[str, float]:
    """
    SL/TP tại swing impulse (Fib).
    BUY: SL đáy (1), TP đỉnh (0). SELL: SL đỉnh (1), TP đáy (0).
    """
    empty = {
        "trades": 0,
        "wins": 0,
        "winrate": 0.0,
        "total_pnl_pct": 0.0,
        "avg_pnl_pct": 0.0,
        "profit_factor": 0.0,
        "stake_usd": float(stake_usd),
        "starting_bankroll_usd": float(starting_bankroll_usd),
        "total_staked_usd": 0.0,
        "total_returned_usd": 0.0,
        "net_pnl_usd": 0.0,
        "ending_bankroll_usd": float(starting_bankroll_usd),
        "return_on_bankroll_pct": 0.0,
        "return_on_staked_pct": 0.0,
        "exit_mode": "swing",
    }
    if not trades:
        return empty

    n = len(close)
    pos_end = -1
    pnls: List[float] = []

    for entry_i, side, entry, sl_price, tp_price in trades:
        if entry_i <= pos_end or entry_i >= n:
            continue
        if side == "BUY" and not (sl_price < entry < tp_price):
            continue
        if side == "SELL" and not (tp_price < entry < sl_price):
            continue

        exit_i = n - 1
        pnl = 0.0
        hit = False
        for j in range(entry_i, n):
            h, l = high[j], low[j]
            if side == "BUY":
                if l <= sl_price:
                    pnl = (sl_price - entry) / entry * 100.0
                    exit_i = j
                    hit = True
                    break
                if h >= tp_price:
                    pnl = (tp_price - entry) / entry * 100.0
                    exit_i = j
                    hit = True
                    break
            else:
                if h >= sl_price:
                    pnl = (entry - sl_price) / entry * 100.0
                    exit_i = j
                    hit = True
                    break
                if l <= tp_price:
                    pnl = (entry - tp_price) / entry * 100.0
                    exit_i = j
                    hit = True
                    break
        if not hit:
            exit_price = float(close[n - 1])
            if side == "BUY":
                pnl = (exit_price - entry) / entry * 100.0
            else:
                pnl = (entry - exit_price) / entry * 100.0
            exit_i = n - 1

        pnls.append(pnl)
        pos_end = exit_i

    wins = sum(1 for p in pnls if p > 0)
    losses = sum(-p for p in pnls if p < 0)
    gains = sum(p for p in pnls if p > 0)
    total_pct = sum(pnls)
    pf = (gains / losses) if losses > 0 else (gains if gains > 0 else 0.0)

    stake = float(stake_usd)
    bankroll0 = float(starting_bankroll_usd)
    pnls_usd = [stake * (p / 100.0) for p in pnls]
    trade_n = len(pnls_usd)
    total_staked = stake * trade_n
    net_usd = float(sum(pnls_usd))
    total_returned = total_staked + net_usd
    ending = bankroll0 + net_usd

    return {
        "trades": trade_n,
        "wins": wins,
        "winrate": 100.0 * wins / trade_n if trade_n else 0.0,
        "total_pnl_pct": total_pct,
        "avg_pnl_pct": total_pct / trade_n if trade_n else 0.0,
        "profit_factor": pf,
        "stake_usd": stake,
        "starting_bankroll_usd": bankroll0,
        "total_staked_usd": round(total_staked, 2),
        "total_returned_usd": round(total_returned, 2),
        "net_pnl_usd": round(net_usd, 2),
        "ending_bankroll_usd": round(ending, 2),
        "return_on_bankroll_pct": round((net_usd / bankroll0 * 100.0) if bankroll0 > 0 else 0.0, 2),
        "return_on_staked_pct": round((net_usd / total_staked * 100.0) if total_staked > 0 else 0.0, 2),
        "exit_mode": "swing",
    }
