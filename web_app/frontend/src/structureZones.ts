import type { Candle } from './indicators'

export type StructureZone = {
  kind: 'support' | 'resistance'
  pivotIdx: number
  startTime: number
  endTime: number
  low: number
  high: number
}

export type StructureZoneParams = {
  pivotLeft?: number
  pivotRight?: number
  atrPeriod?: number
  zoneAtrMult?: number
  maxPerKind?: number
}

function computeAtr(candles: Candle[], period: number): number[] {
  const n = candles.length
  const atr = new Array<number>(n).fill(NaN)
  if (n < period + 1) return atr

  const tr = new Array<number>(n).fill(0)
  for (let i = 1; i < n; i++) {
    const h = candles[i].high
    const l = candles[i].low
    const pc = candles[i - 1].close
    tr[i] = Math.max(h - l, Math.abs(h - pc), Math.abs(l - pc))
  }

  let sum = 0
  for (let i = 1; i <= period; i++) sum += tr[i]
  atr[period] = sum / period
  for (let i = period + 1; i < n; i++) {
    atr[i] = (atr[i - 1]! * (period - 1) + tr[i]) / period
  }
  return atr
}

function isPivotLow(candles: Candle[], i: number, left: number, right: number): boolean {
  const v = candles[i].low
  for (let j = i - left; j <= i + right; j++) {
    if (j === i) continue
    if (candles[j].low < v) return false
  }
  return true
}

function isPivotHigh(candles: Candle[], i: number, left: number, right: number): boolean {
  const v = candles[i].high
  for (let j = i - left; j <= i + right; j++) {
    if (j === i) continue
    if (candles[j].high > v) return false
  }
  return true
}

/**
 * Định nghĩa B:
 * - HT (support): pivot đáy với đáy cao hơn đáy pivot trước (higher low) trong uptrend.
 * - KC (resistance): pivot đỉnh với đỉnh thấp hơn đỉnh pivot trước (lower high) trong downtrend.
 */
export function computeStructureZonesB(candles: Candle[], params: StructureZoneParams = {}): StructureZone[] {
  const pivotLeft = params.pivotLeft ?? 5
  const pivotRight = params.pivotRight ?? 5
  const atrPeriod = params.atrPeriod ?? 14
  const zoneAtrMult = params.zoneAtrMult ?? 0.5
  const n = candles.length
  if (n < pivotLeft + pivotRight + 3) return []

  const atr = computeAtr(candles, atrPeriod)
  const endTime = candles[n - 1].time
  const supports: StructureZone[] = []
  const resistances: StructureZone[] = []

  let prevPivotLow: number | null = null
  let prevPivotHigh: number | null = null

  for (let i = pivotLeft; i < n - pivotRight; i++) {
    const thick = (atr[i] > 0 ? atr[i] : candles[i].close * 0.005) * zoneAtrMult

    if (isPivotLow(candles, i, pivotLeft, pivotRight)) {
      const low = candles[i].low
      if (prevPivotLow != null && low > prevPivotLow) {
        supports.push({
          kind: 'support',
          pivotIdx: i,
          startTime: candles[i].time,
          endTime,
          low,
          high: low + thick,
        })
      }
      prevPivotLow = low
    }

    if (isPivotHigh(candles, i, pivotLeft, pivotRight)) {
      const high = candles[i].high
      if (prevPivotHigh != null && high < prevPivotHigh) {
        resistances.push({
          kind: 'resistance',
          pivotIdx: i,
          startTime: candles[i].time,
          endTime,
          high,
          low: high - thick,
        })
      }
      prevPivotHigh = high
    }
  }

  return pickZonesForTrend(supports, resistances)
}

/** Uptrend: 2 HT cao nhất (gần giá). Downtrend: 2 KC cao nhất. Không trộn HT+KC cùng lúc. */
export function pickZonesForTrend(
  supports: StructureZone[],
  resistances: StructureZone[],
): StructureZone[] {
  const topSupports = [...supports].sort((a, b) => b.low - a.low).slice(0, 2)
  const topResistances = [...resistances].sort((a, b) => b.high - a.high).slice(0, 2)

  const up =
    supports.length >= 2 && supports[supports.length - 1].low > supports[supports.length - 2].low
  const down =
    resistances.length >= 2 &&
    resistances[resistances.length - 1].high < resistances[resistances.length - 2].high

  if (up && !down) return topSupports
  if (down && !up) return topResistances

  if (up && down) {
    const lastSupport = supports[supports.length - 1].pivotIdx
    const lastResistance = resistances[resistances.length - 1].pivotIdx
    return lastSupport >= lastResistance ? topSupports : topResistances
  }

  return []
}
