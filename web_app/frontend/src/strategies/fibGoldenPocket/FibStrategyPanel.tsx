import React from 'react'
import type { FibGoldenParams } from './types'

type Props = {
  fibParams: FibGoldenParams
  setFibParams: React.Dispatch<React.SetStateAction<FibGoldenParams>>
}

export function FibStrategyPanel({ fibParams, setFibParams }: Props) {
  return (
    <>
      <div style={{ fontSize: 12, opacity: 0.9, marginBottom: 8 }}>
        Fib Golden Pocket — vùng {fibParams.fib_zone_low}–{fibParams.fib_zone_high} sau impulse tăng (BUY) / giảm (SELL)
      </div>
      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center' }}>
        <label style={{ fontSize: 12, opacity: 0.85 }}>
          days_back{' '}
          <input
            type="number"
            min={30}
            max={3650}
            value={fibParams.days_back}
            onChange={(e) => setFibParams((p) => ({ ...p, days_back: Number(e.target.value) }))}
            style={{ width: 90, marginLeft: 6 }}
          />
        </label>
        <label style={{ fontSize: 12, opacity: 0.85 }}>
          pivot L/R{' '}
          <input
            type="number"
            min={1}
            max={20}
            value={fibParams.pivot_left}
            onChange={(e) =>
              setFibParams((p) => ({ ...p, pivot_left: Number(e.target.value), pivot_right: Number(e.target.value) }))
            }
            style={{ width: 40, marginLeft: 4 }}
          />
          <input
            type="number"
            min={1}
            max={20}
            value={fibParams.pivot_right}
            onChange={(e) => setFibParams((p) => ({ ...p, pivot_right: Number(e.target.value) }))}
            style={{ width: 40, marginLeft: 4 }}
          />
        </label>
        <label style={{ fontSize: 12, opacity: 0.85 }}>
          min impulse %{' '}
          <input
            type="number"
            step="0.1"
            min={0.2}
            max={50}
            value={fibParams.min_impulse_pct}
            onChange={(e) => setFibParams((p) => ({ ...p, min_impulse_pct: Number(e.target.value) }))}
            style={{ width: 60, marginLeft: 6 }}
          />
        </label>
        <label style={{ fontSize: 12, opacity: 0.85 }}>
          min bars{' '}
          <input
            type="number"
            min={3}
            max={200}
            value={fibParams.min_impulse_bars}
            onChange={(e) => setFibParams((p) => ({ ...p, min_impulse_bars: Number(e.target.value) }))}
            style={{ width: 55, marginLeft: 6 }}
          />
        </label>
        <label style={{ fontSize: 12, opacity: 0.85 }}>
          max pullback bars{' '}
          <input
            type="number"
            min={10}
            max={500}
            value={fibParams.max_pullback_bars}
            onChange={(e) => setFibParams((p) => ({ ...p, max_pullback_bars: Number(e.target.value) }))}
            style={{ width: 65, marginLeft: 6 }}
          />
        </label>
        <label style={{ fontSize: 12, opacity: 0.85 }} title="Gom tín hiệu gần nhau, tránh BUY+SELL cạnh nhau">
          spacing bars{' '}
          <input
            type="number"
            min={0}
            max={500}
            value={fibParams.min_signal_spacing_bars}
            onChange={(e) => setFibParams((p) => ({ ...p, min_signal_spacing_bars: Number(e.target.value) }))}
            style={{ width: 55, marginLeft: 6 }}
          />
        </label>
        <label style={{ fontSize: 12, opacity: 0.85 }}>
          Fib zone{' '}
          <input
            type="number"
            step="0.01"
            min={0.1}
            max={0.9}
            value={fibParams.fib_zone_low}
            onChange={(e) => setFibParams((p) => ({ ...p, fib_zone_low: Number(e.target.value) }))}
            style={{ width: 55, marginLeft: 4 }}
          />
          –
          <input
            type="number"
            step="0.01"
            min={0.2}
            max={0.95}
            value={fibParams.fib_zone_high}
            onChange={(e) => setFibParams((p) => ({ ...p, fib_zone_high: Number(e.target.value) }))}
            style={{ width: 55, marginLeft: 4 }}
          />
        </label>
        <label style={{ fontSize: 12, display: 'flex', alignItems: 'center', gap: 4 }}>
          <input
            type="checkbox"
            checked={fibParams.require_bullish_close}
            onChange={(e) => setFibParams((p) => ({ ...p, require_bullish_close: e.target.checked }))}
          />
          nến xanh (long)
        </label>
        <label style={{ fontSize: 12, display: 'flex', alignItems: 'center', gap: 4 }}>
          <input
            type="checkbox"
            checked={fibParams.require_bearish_close}
            onChange={(e) => setFibParams((p) => ({ ...p, require_bearish_close: e.target.checked }))}
          />
          nến đỏ (short)
        </label>
        <label style={{ fontSize: 12, opacity: 0.85 }}>
          $/lệnh{' '}
          <input
            type="number"
            min={1}
            value={fibParams.stake_usd}
            onChange={(e) => setFibParams((p) => ({ ...p, stake_usd: Number(e.target.value) }))}
            style={{ width: 72, marginLeft: 4 }}
          />
        </label>
        <label style={{ fontSize: 12, opacity: 0.85 }}>
          vốn gốc ${' '}
          <input
            type="number"
            min={1}
            value={fibParams.starting_bankroll_usd}
            onChange={(e) => setFibParams((p) => ({ ...p, starting_bankroll_usd: Number(e.target.value) }))}
            style={{ width: 80, marginLeft: 4 }}
          />
        </label>
      </div>
      <div style={{ fontSize: 11, opacity: 0.65, marginTop: 8 }}>
        Uptrend: đáy→đỉnh, hồi vào 50–61.8% → BUY. Downtrend: đỉnh→đáy, hồi lên vùng → SELL. Entry = open bar sau tín hiệu.
        SL/TP theo swing: LONG → SL đáy impulse, TP đỉnh · SHORT → SL đỉnh, TP đáy. Thống kê ${fibParams.stake_usd}/lệnh (1 lệnh/lúc).
      </div>
    </>
  )
}
