---
name: honest-backtest
description: >-
  Use this skill whenever backtesting, comparing, tuning TP/SL, or reporting statistics (win rate,
  profit, number of trades) for any trading strategy in this repo (DOGEUSDT / Binance USD-M Futures).
  It lists the rules a backtest must follow and the mistakes already made here, and provides a
  reusable harness that enforces them.
---

# Honest backtest

Lessons learned on this project (2026-10). Follow every rule before reporting a number to the user.

## Mistakes already made here (do not repeat)

1. **Silent horizon cap = survivorship bias.** The old `backtest_doge_3m_degen` only looked 1440
   candles (3 days) ahead. A trade that had not hit TP/SL by then was dropped (not recorded) and
   the loop moved on, so later signals were taken while that trade would really still be open.
   The list looked clean (0 overlaps) but contained ~413 trades the real bot could never take,
   mostly fast winners, while the slow losers vanished: **656 trades / 90.4% win** instead of the
   true **374 trades / 75.7% win**. Each trade looked correct when clicked; the *set* was wrong.
2. **"No overlaps" is not proof of one-position-at-a-time.** Also check that no trade was
   dropped: every signal must end up as taken, ignored-because-open, or skipped-with-reason.
3. **Win rate without the payoff ratio is meaningless.** TP 5% / SL 15% needs >75% wins just to
   break even; 75.7% was ~zero edge after fees.
4. **Best-of-grid is not an expected result.** A TP/SL grid on the full history gave +263% for
   8%/25% but +57% for 8%/30%: noise / overfitting. Never present the best cell as the plan.
5. **Verify, don't assume.** Run code on the real DB and compare independently before
   explaining a discrepancy. Say clearly what was and was not checked.

## Rules for every backtest

- **One position at a time.** A signal while a position is open is ignored.
- **No silent cap.** A trade runs until TP/SL, or until an *explicit* time-stop that exits at
  market and **is counted**. A trade still open at the end of data is marked to market and
  reported separately (it blocks later signals).
- **No look-ahead.** Signal decided on a *closed* bar; rolling highs/lows use `shift(1)`;
  entry at the **open of the next candle**.
- **Intrabar order unknown:** TP and SL touched in the same candle → **SL first**. Gap through
  SL → fill at the candle open. Check exits on the 3m data even for higher timeframes.
- **Costs:** taker fee 0.05%/side + slippage 0.02%/side + funding 0.01%/8h held.
- **Data:** Binance USD-M **Futures** only (`klines_dogeusdt_3m`); assert no duplicate times;
  report gaps.
- **Validation:** pick parameters on **in-sample** (before 2025-01-01) only, then report
  **out-of-sample**. Report how many combinations were tested, per-year results, max drawdown,
  profit factor, trades/month, and how robust neighbouring parameters are.
- **Self-check the harness** against a known result first (DOGE_3M_DEGEN 5/15 → ~374 closed
  trades, ~75.7% win).
- Never change the live bot, its TP/SL, or rows in the `trades` table without the user's OK.
  Back up `trading_bot.db` before any DB write.

## Tools

- [bt_harness.py](./scripts/bt_harness.py): data loading/resampling, indicators, `Sim.run`
  (enforces all rules above), `check_trades`, `metrics`, `per_year`.
- [strategy_search.py](./scripts/strategy_search.py): harness self-check + grid of classic
  strategies on 15m/1h/4h, selected on in-sample only.

Run on the VPS (the DB lives there):

```bash
scp .agents/skills/honest-backtest/scripts/*.py root@165.101.47.50:/tmp/
ssh root@165.101.47.50 "cd /root/tramiune005_bot_train_trade/web_app/backend && \
  source .venv/bin/activate && PYTHONPATH=.:/tmp python /tmp/strategy_search.py"
```

Before reporting: confirm the self-check matches, `check_trades` passed, and quote OOS numbers
next to IS numbers.
