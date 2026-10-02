/** Signal row shared by all strategies on the chart UI. */
export type ChartSignal = {
  side: 'BUY' | 'SELL'
  idx: number
  entry_idx?: number
  signal_close?: number
  entry_open: number
  price: number
  trend?: 'up' | 'down'
  rsi?: number
  upper?: number
  lower?: number
  high_volume?: boolean
  zone_low?: number
  zone_high?: number
  level_50?: number
  level_618?: number
  fib_anchor_0?: number
  fib_anchor_1?: number
  sl_price?: number
  tp_price?: number
}
