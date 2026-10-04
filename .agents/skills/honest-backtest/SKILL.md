---
name: honest-backtest
description: >-
  Use this skill whenever backtesting, comparing, tuning TP/SL, or reporting statistics (win rate,
  profit, number of trades) for any trading strategy in this repo (Binance USD-M Futures: DOGE, XRP, SOL, ETH, BTC).
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
- **Limit orders may not fill.** Use `Sim.run_limit`: entry only when price trades *through* the
  limit within the validity window; TP-in-fill-candle not allowed; maker fee on limit legs, taker +
  slippage on SL/time-stop. Report how many orders went unfilled. The live 19:45 order did not fill.
- **Check the edge before costs too** (gross EV). If gross EV is ~0, no fee level will save it.
- Never change the live bot, its TP/SL, or rows in the `trades` table without the user's OK.
  Back up `trading_bot.db` before any DB write.

## Results so far (DOGEUSDT futures, 2022-09 → 2026-10)

| Test | Result |
|---|---|
| DOGE_3M_DEGEN 5/15 (live) | 374 trades, 75.7% win, **−42% after real costs** |
| 648 classic combos (Donchian/EMA/RSI/BB/squeeze, 15m/1h/4h) | 15m: none survive costs. Best robust: **4h Donchian100** (12/12 exit settings positive IS and OOS, beats random 79–99%), but only ~2.7 trades/month and 2023 −42% |
| Mean-reversion scalping 5m/15m (BB limit, BB market, RSI2 limit), 288 configs | **0/288 profitable out-of-sample**; even before costs best OOS gross EV ≈ +0.01%/trade. Limit entries at the band are adversely selected. Highest win rate (RSI2, ~62%) still loses |
| XRP 5m "Nada + RSI + Volume" (user's TradingView script, h=8, mult=3, RSI 20/80, vol<2x) | Only **73 signals in 4 years** (~1.5/month). Original (reverse, no TP/SL): 34 trades, IS −22% / OOS +112%, unstable. TP/SL grid: tiny TP + huge SL wins ~100% but the worst adverse move before TP was −9% (TP0.5%) / −15% (TP1%), so the tail decides; 72 trades with 0 losses cannot prove a loss rate below the 3.4% break-even. Steadiest zone TP 0.75–1% / SL 2–3%: ~+0.2%/trade, ~16–17% total over 4 years at 1x, CI touches 0 |
| Same XRP signals, **high R:R** (TP = RR x SL), 42 cells | Much better: zone **SL 0.75–1.5%, RR 8–15** positive IS and OOS. SL1%/RR10: 68 trades, 16 TP (23.5% vs 10.4% break-even), +95% at 1x, beats 100% of random entries, still +65% without the 3 best trades; 2022 0/6, 2025 dominates. Very tight SL (0.3%) ~flat. Only ~16 wins: wide uncertainty |
| Loosening the XRP signal (h 6/8/10, mult 2/2.5/3, RSI 20/80–30/70, vol 2/3/off) x 9 high-R:R exits = 729 runs | Loosening **hurts**: RSI 25/75 or 30/70 and removing the volume filter give 5–30x more trades but lose in-sample. The original (h8, mult3, RSI 20/80, vol<2x) is the best IS setting and 9/9 exits positive in both periods; close neighbours (h6/h10, vol<3x) stay positive. Only 6/81 settings positive in both periods |
| XRP NW+RSI+Volume signal, original params, on XRP/DOGE/SOL/ETH/BTC, R:R 2–3 | **Does not generalise**: only XRP positive (12/12 exits); DOGE, SOL, ETH lose in all exits, BTC ~flat. Pooled: negative in 11/12 exits. The XRP edge is likely coin/period specific (overfit risk) |
| 4h Donchian 55/100 breakout, SL 1.5–2 ATR, R:R 2–3, same params on 5 coins | Generalises to **altcoins** (DOGE, XRP, SOL positive), **not ETH/BTC**. Pooled 5 coins: positive in 7/8 settings, win ~38–40% at RR 2, ~0.2–0.5%/trade, ~3 trades/month/coin. Best simple candidate so far |
| Pure candlestick price action (engulfing, pin bar, inside bar, ± at 20-bar extreme), 1h/4h, 5 coins, RR 0.5–2 (240 combos) | Win rate ≈ break-even 1/(1+RR) everywhere (RR1 ≈ 49–53%, RR2 ≈ 32–36%) → candles alone ≈ random; after costs almost all lose. **0** coin-level combos with win ≥ 70% at RR ≥ 1. Best: 4h engulfing at 20-bar extreme RR1 ≈ +0.02%/trade (flat) |
| Bulkowski top multi-candle patterns (three line strike, crows/soldiers, morning/evening star, ± prior-trend), 1h/4h/1d, 5 coins (270 cells) | "Breakout first" rate reproduces the famous 74–93% (three line strike ~81%) **but it is an artefact**: the boundary in the predicted direction sits next to the close, the other far away. Trade win rates ≈ break-even; 0 cells with win ≥ 70% at RR ≥ 1. Only 4h morning/evening star after a prior move is positive in IS and OOS at RR 1–2 (RR1: 546 trades, 56.8% win, +0.28%/trade), driven by DOGE/XRP; BTC/ETH negative. 1d crows/soldiers: too few trades (9–25) |
| DOGE deep dive: 4h star after prior counter-move (default params) | RR1: 117 trades, 60.7% win, +0.145R/trade (90% CI −0.006…+0.29), IS +10.8R / OOS +6.1R, every year positive, long and short both positive, beats 100% of random entries; RR1.5 similar (+0.16R), RR2 ≈ 0. Neighbourhood: 23/24 positive IS, 14/24 both; look-back 5 bars weaker. 1% risk/trade: +18% in 4 y, maxDD 5%. **Combined with 4h Donchian100** (monthly corr −0.17): 251 trades, +50.8R, 1% risk each → +63%, maxDD 11%, only 2023 negative |
| Nadaraya-Watson 5m **scalping** (non-repainting NW; band re-entry, + RSI 30/70, NW slope flip; 2h time-stop), 5 coins, 21 configs each | **0/105** coin-configs positive in either period. Gross EV ≈ 0.000–0.01%/trade everywhere, net ≈ −0.14% (= costs). 80–500 trades/coin/month. No edge to protect, so fees decide. Warn users: the popular LuxAlgo NW envelope repaints by default |
| "Learn from losing trades" filters on the NW 5m scalp (9 causal features, additive bin score, keep top 10–30%), 5 coins, 2024-01 → 2026-10 | **Walk-forward (learn only from finished past trades, refit quarterly): no improvement** (net/trade −0.09…−0.16% vs −0.11…−0.14% unfiltered). Even the in-sample "cheating" filter stays negative (−0.01…−0.08%/trade). Filtering cannot create an edge that is not there; loss-analysis filters must always be validated walk-forward |

## Tools

- [bt_harness.py](./scripts/bt_harness.py): data loading/resampling, indicators, `Sim.run`
  (enforces all rules above), `check_trades`, `metrics`, `per_year`.
- [bt_data.py](./scripts/bt_data.py): download official Binance USD-M futures klines (any symbol /
  interval) from data.binance.vision with SHA256 check into `data/futures_um/` (local machine).
- [mr_search.py](./scripts/mr_search.py): mean-reversion scalping grid on 1m data, multiprocessing
  (`SYMBOL=SOLUSDT` env to switch coin after downloading it).
- [xrp_nada.py](./scripts/xrp_nada.py): 1:1 port of the user's TradingView XRP NW+RSI+Volume script, TP/SL grid, bootstrap CI, random baseline.
- [xrp_nada_rr.py](./scripts/xrp_nada_rr.py): high R:R grid for the same signals, leave-best-trades-out check.
- [xrp_nada_loosen.py](./scripts/xrp_nada_loosen.py): signal-parameter loosening study (IS-only selection).
- [nada_cross_coin.py](./scripts/nada_cross_coin.py), [donchian_cross_coin.py](./scripts/donchian_cross_coin.py): same parameters on 5 coins (best anti-overfit check).
- [price_action.py](./scripts/price_action.py): candlestick patterns on 5 coins.
- [candle_clusters.py](./scripts/candle_clusters.py): Bulkowski multi-candle patterns, breakout-rate vs trade win-rate.
- [doge_star_deep.py](./scripts/doge_star_deep.py): DOGE 4h star deep dive (per year, random, neighbourhood, risk sizing, Donchian combo).
- [nada_scalp.py](./scripts/nada_scalp.py): NW 5m scalping families on 5 coins.
- [loss_filter_wf.py](./scripts/loss_filter_wf.py): walk-forward vs in-sample loss-learning filters (template for any strategy).
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
