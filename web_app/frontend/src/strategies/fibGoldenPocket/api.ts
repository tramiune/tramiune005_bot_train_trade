import type { FibGoldenParams } from './types'
import { STRATEGY_ID } from './defaults'

export function backtestUrl(apiBase: string, symbol: string, timeframe: string, params: FibGoldenParams) {
  const url = new URL(`${apiBase}/api/backtest/${STRATEGY_ID}`)
  url.searchParams.set('symbol', symbol)
  url.searchParams.set('timeframe', timeframe)
  url.searchParams.set('days_back', String(params.days_back))
  url.searchParams.set('pivot_left', String(params.pivot_left))
  url.searchParams.set('pivot_right', String(params.pivot_right))
  url.searchParams.set('min_impulse_pct', String(params.min_impulse_pct))
  url.searchParams.set('min_impulse_bars', String(params.min_impulse_bars))
  url.searchParams.set('max_pullback_bars', String(params.max_pullback_bars))
  url.searchParams.set('min_signal_spacing_bars', String(params.min_signal_spacing_bars))
  url.searchParams.set('fib_zone_low', String(params.fib_zone_low))
  url.searchParams.set('fib_zone_high', String(params.fib_zone_high))
  url.searchParams.set('require_bullish_close', String(params.require_bullish_close))
  url.searchParams.set('require_bearish_close', String(params.require_bearish_close))
  url.searchParams.set('stake_usd', String(params.stake_usd))
  url.searchParams.set('starting_bankroll_usd', String(params.starting_bankroll_usd))
  return url
}
