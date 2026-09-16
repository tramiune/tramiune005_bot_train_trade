# Trading Rules Journal (Updated)

This document records the trading lessons learned from backtesting, quantitative analysis, and stress testing.

## Strategy 1: SMA Crossover (Trend Following)
* **Timeframe**: 1H (Filters out 15m noise)
* **Moving Averages**: Fast 9, Slow 21
* **Trend Filter**: Only LONG when `Price > EMA 200`
* **Momentum Filter**: `RSI(14) > 50` (Don't fight the trend)
* **Risk/Reward**: 2.0
* **Result**: Steady ~40% Winrate over 4 years. A highly robust, low-maintenance trend-following engine.

---

## Strategy 2: Smart Money Concept (Dip Buying / Liquidity Sweep)
A highly optimized, sniper-like strategy for Bitcoin that buys panic dips using volume anomalies.

### Core Logic:
1. **Trend is Up**: `Price > EMA 200`
2. **Liquidity Sweep**: Price drops below the Lower Bollinger Band (SMA 20 - 2 STD).
3. **Smart Money Footprint**: Volume is significantly higher than the 20-period moving average.
4. **Rejection**: The candle closes in the upper 50% of its range (Pinbar / Hammer).

### Advanced "God Mode" Filters (Learned from Loss Analysis):
1. **The Falling Knife Filter**: Do not buy if the 5-hour price drop exceeds `0.6%`. Fast crashes cut through support.
2. **The Over-extension Filter**: Do not buy if the price is > `2.0%` above the EMA 200. Drops from high altitudes are often deep corrections, not shallow dips.
3. **The "Monday Fakeout" Rule**: Do not trade on Mondays (`dayofweek != 0`). Institutional money often creates fake trends at the start of the week.
4. **The Goldilocks Volume**: Volume must be `> 1.5x` but `< 2.0x`. Extreme volume spikes (> 2.0x) represent capitulation/liquidation cascades, not simple shakeouts.

**BTC Result**: ~58% Winrate at 2.0 RR over 4 years. (Elite tier performance).

---

## 🚨 Critical Meta-Lesson: OVERFITTING 🚨
* **The Trap**: The "God Mode" filters above were derived strictly from Bitcoin's historical data.
* **The Consequence**: When applied blindly to Altcoins (ETH, SOL, BNB, ADA), the winrate collapsed to ~23% and the system hemorrhaged money.
* **The Reason**: Altcoins have fundamentally different volatility and volume profiles. A 0.6% drop is a crash for BTC, but just normal noise for SOL.
* **The Solution**: 
  1. Use **Dynamic Parameters** (e.g., using ATR instead of fixed percentages).
  2. Treat every coin as a unique organism. **Build and optimize separate strategies/parameters for each individual coin.**

---

## Strategy 3: ETH Volatility Squeeze Breakout (Trend Initiation)
Built specifically for Ethereum (ETH) to catch massive trend continuations with a strict Risk/Reward of 5.0.

### Core Logic:
1. **Squeeze Detection**: Bollinger Bands (20, 2) must be inside Keltner Channels (20, 1.5). This indicates a period of abnormally low volatility.
2. **The Breakout**: Price closes above the Upper Bollinger Band, and the 1H candle is in an uptrend (Close > EMA 200).
3. **Target & Stop**: RR = 5.0. Stop Loss is super tight (Low of the breakout candle or `0.5 * ATR`).

### Advanced "Sniper" Filters (Learned from 156 Losses):
1. **Volume Sweet Spot**: Breakout volume must be `> 2.0x` and `< 3.0x` the average. Too low = fakeout. Too high = exhaustion/climactic top.
2. **Candle Size Limit**: The breakout candle body must be `< 2.0%` of price. Massive 3%+ candles leave no momentum for continuation.
3. **EMA Gravity Trap**: The breakout must happen when price is already `> 1.0%` away from the EMA 200. Breakouts occurring exactly on the EMA 200 get sucked back in.
4. **Squeeze Duration Trap**: The squeeze must last `< 6 hours`. If a 1H squeeze lasts 12+ hours, it's just a dead, illiquid market, and the resulting breakout is usually a random low-volume fakeout.
5. **The Monday Fakeout**: Never trade on Mondays.
6. **Momentum Backing (RSI/Session)**: The highest probability breakouts happen during the London Session (9h-13h UTC) when pre-breakout RSI is already overbought (> 70).

**ETH Result**: ~44.8% Winrate at 5.0 RR over 4 years. (Incredible profitability, but requires iron discipline to handle long periods with no trades).
