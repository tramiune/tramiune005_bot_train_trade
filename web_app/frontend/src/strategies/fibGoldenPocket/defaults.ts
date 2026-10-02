import type { FibGoldenParams } from './types'

export const STRATEGY_ID = 'fib_golden_pocket' as const

export const DEFAULT_FIB_PARAMS: FibGoldenParams = {
  days_back: 180,
  pivot_left: 5,
  pivot_right: 5,
  min_impulse_pct: 1.5,
  min_impulse_bars: 8,
  max_pullback_bars: 120,
  min_signal_spacing_bars: 24,
  fib_zone_low: 0.5,
  fib_zone_high: 0.618,
  require_bullish_close: true,
  require_bearish_close: true,
  sl_pct: 2,
  tp_pct: 5,
  stake_usd: 100,
  starting_bankroll_usd: 1000,
}
