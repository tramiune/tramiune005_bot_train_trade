export type FibGoldenParams = {
  days_back: number
  pivot_left: number
  pivot_right: number
  min_impulse_pct: number
  min_impulse_bars: number
  max_pullback_bars: number
  min_signal_spacing_bars: number
  fib_zone_low: number
  fib_zone_high: number
  require_bullish_close: boolean
  require_bearish_close: boolean
  sl_pct: number
  tp_pct: number
  stake_usd: number
  starting_bankroll_usd: number
}

export type StrategyPnlStats = {
  trades: number
  wins: number
  winrate: number
  stake_usd: number
  starting_bankroll_usd: number
  total_staked_usd: number
  total_returned_usd: number
  net_pnl_usd: number
  ending_bankroll_usd: number
  return_on_bankroll_pct: number
  return_on_staked_pct?: number
  sl_pct?: number
  tp_pct?: number
}

export type FibSetup = {
  direction: 'up' | 'down'
  from_time: number
  to_time: number
  zone_low: number
  zone_high: number
  levels: Record<string, number>
}

export type FibStrategySignal = {
  side: 'BUY' | 'SELL'
  trend?: 'up' | 'down'
  idx: number
  entry_idx?: number
  signal_close?: number
  entry_open: number
  price: number
  zone_low?: number
  zone_high?: number
  level_50?: number
  level_618?: number
  fib_anchor_0?: number
  fib_anchor_1?: number
}
