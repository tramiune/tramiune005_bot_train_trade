import React, { useEffect, useMemo, useRef, useState } from 'react'
import {
  createChart,
  CrosshairMode,
  IChartApi,
  ISeriesApi,
  CandlestickSeries,
  UTCTimestamp,
  type CandlestickData,
} from 'lightweight-charts'

type Timeframe = '1m' | '5m' | '15m' | '1h' | '4h' | '1d'

type Candle = { time: number; open: number; high: number; low: number; close: number }
type Marker = {
  time: number
  position: 'aboveBar' | 'belowBar'
  color: string
  shape: 'arrowUp' | 'arrowDown'
  text: string
}

function tfToMinutes(tf: Timeframe): number {
  switch (tf) {
    case '1m':
      return 1
    case '5m':
      return 5
    case '15m':
      return 15
    case '1h':
      return 60
    case '4h':
      return 240
    case '1d':
      return 1440
  }
}

function chunkSize(tf: Timeframe) {
  // Aim for "a bit more than viewport" per chunk.
  const m = tfToMinutes(tf)
  if (m <= 1) return 1200
  if (m <= 5) return 1500
  if (m <= 15) return 2000
  return 2500
}

function daysForCandles(tf: Timeframe, candles: number) {
  const minutes = candles * tfToMinutes(tf)
  return Math.max(1, Math.ceil(minutes / (24 * 60)))
}

function apiBase() {
  const host = window.location.hostname || 'localhost'
  return `http://${host}:8000`
}

function toChartCandle(c: Candle): CandlestickData<UTCTimestamp> {
  return { ...c, time: c.time as UTCTimestamp }
}

export function App() {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const seriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null)
  const candlesRef = useRef<Candle[]>([])
  const oldestTimeRef = useRef<number | null>(null)
  const loadingMoreRef = useRef(false)
  const rangeDebounceRef = useRef<number | null>(null)

  const [symbols, setSymbols] = useState<string[]>([])
  const [symbol, setSymbol] = useState('BTCUSDT')
  const [timeframe, setTimeframe] = useState<Timeframe>('15m')
  const [daysBack, setDaysBack] = useState(30)
  const [status, setStatus] = useState<string>('ready')
  const [error, setError] = useState<string>('')
  const [summary, setSummary] = useState<{ trades: number; avg_r: number; winrate: number } | null>(null)

  const resize = () => {
    if (!containerRef.current || !chartRef.current) return
    chartRef.current.applyOptions({
      width: containerRef.current.clientWidth,
      height: containerRef.current.clientHeight,
    })
  }

  useEffect(() => {
    ;(async () => {
      try {
        setError('')
        const res = await fetch(`${apiBase()}/api/symbols`)
        const data = await res.json()
        setSymbols(data.symbols ?? [])
      } catch (e: any) {
        setError(`Cannot reach backend at ${apiBase()} (symbols).`)
      }
    })()
  }, [])

  useEffect(() => {
    if (!containerRef.current) return
    try {
      const chart = createChart(containerRef.current, {
        layout: { background: { color: '#0e1117' }, textColor: '#e0e0ff' },
        grid: { vertLines: { color: '#1f2937' }, horzLines: { color: '#1f2937' } },
        crosshair: { mode: CrosshairMode.Normal },
        rightPriceScale: { borderColor: '#283244' },
        timeScale: { borderColor: '#283244', timeVisible: true, secondsVisible: false },
        width: containerRef.current.clientWidth,
        height: containerRef.current.clientHeight,
      })
      // lightweight-charts v5 uses addSeries(CandlestickSeries, options)
      const series = chart.addSeries(CandlestickSeries, {
        upColor: '#26a69a',
        downColor: '#ef5350',
        wickUpColor: '#26a69a',
        wickDownColor: '#ef5350',
        borderVisible: false,
      })

      chartRef.current = chart
      seriesRef.current = series

      const onRange = () => {
        if (rangeDebounceRef.current) window.clearTimeout(rangeDebounceRef.current)
        rangeDebounceRef.current = window.setTimeout(() => {
          const ts = chartRef.current?.timeScale()
          if (!ts) return
          const r: any = ts.getVisibleRange?.()
          const from = r?.from
          const oldest = oldestTimeRef.current
          if (!from || !oldest) return
          // If user is close to the left edge, load older data
          const threshold = tfToMinutes(timeframe) * 60 * 200 // ~200 bars in seconds
          if (from < oldest + threshold) void loadMoreOlder()
        }, 200)
      }

      // lightweight-charts timeScale subscription (v4/v5)
      ;(chart.timeScale() as any).subscribeVisibleTimeRangeChange?.(onRange)

      window.addEventListener('resize', resize)
      return () => {
        window.removeEventListener('resize', resize)
        ;(chart.timeScale() as any).unsubscribeVisibleTimeRangeChange?.(onRange)
        chart.remove()
        chartRef.current = null
        seriesRef.current = null
      }
    } catch (e: any) {
      setError(`Chart init error: ${String(e?.message ?? e)}`)
      setStatus('error')
      return
    }
  }, [])

  const fetchChunk = async (opts: { endTime?: number }) => {
    const url = new URL(`${apiBase()}/api/ohlcv`)
    url.searchParams.set('symbol', symbol)
    url.searchParams.set('timeframe', timeframe)
    url.searchParams.set('limit', String(chunkSize(timeframe)))
    url.searchParams.set('days_back', String(daysForCandles(timeframe, chunkSize(timeframe))))
    url.searchParams.set('exchange', 'binance')
    if (opts.endTime) url.searchParams.set('end_time', String(opts.endTime))

    const res = await fetch(url.toString())
    return (await res.json()) as any
  }

  const loadCandles = async () => {
    setStatus('loading candles...')
    setSummary(null)
    setError('')
    let data: any
    try {
      data = await fetchChunk({})
    } catch (e: any) {
      setError(`Cannot reach backend at ${apiBase()} (ohlcv).`)
      setStatus('error')
      return
    }
    const candles: Candle[] = data.candles ?? []
    candlesRef.current = candles
    oldestTimeRef.current = candles.length ? candles[0].time : null
    seriesRef.current?.setData(candles.map(toChartCandle))
    ;(seriesRef.current as any)?.setMarkers?.([])
    chartRef.current?.timeScale().fitContent()
    setStatus(`loaded ${candles.length} candles`)
  }

  const loadMoreOlder = async () => {
    if (loadingMoreRef.current) return
    const oldest = oldestTimeRef.current
    if (!oldest) return

    loadingMoreRef.current = true
    setStatus('loading more history...')
    try {
      const data = await fetchChunk({ endTime: oldest })
      const older: Candle[] = data.candles ?? []
      if (!older.length) {
        setStatus('no more history')
        return
      }

      // Deduplicate overlap
      const cur = candlesRef.current
      const newestOlderTime = older[older.length - 1]?.time
      const dedupedOlder = newestOlderTime && cur.length && newestOlderTime >= cur[0].time
        ? older.filter((c) => c.time < cur[0].time)
        : older

      if (!dedupedOlder.length) {
        setStatus('history up to date')
        return
      }

      const merged = [...dedupedOlder, ...cur]
      candlesRef.current = merged
      oldestTimeRef.current = merged[0]?.time ?? oldestTimeRef.current

      seriesRef.current?.setData(merged.map(toChartCandle))
      setStatus(`loaded ${merged.length} candles`)
    } catch (e: any) {
      setError(`Cannot reach backend at ${apiBase()} (ohlcv).`)
      setStatus('error')
    } finally {
      loadingMoreRef.current = false
    }
  }

  const runBacktest = async () => {
    setStatus('backtesting...')
    setError('')
    const url = new URL(`${apiBase()}/api/backtest/sma_cross`)
    url.searchParams.set('symbol', symbol)
    url.searchParams.set('timeframe', timeframe)
    url.searchParams.set('days_back', String(Math.max(daysBack, 180)))
    url.searchParams.set('rr', '2.0')
    let data: any
    try {
      const res = await fetch(url.toString(), { method: 'POST' })
      data = await res.json()
    } catch (e: any) {
      setError(`Cannot reach backend at ${apiBase()} (backtest).`)
      setStatus('error')
      return
    }
    const candles: Candle[] = data.candles ?? []
    const markers: Marker[] = data.markers ?? []
    seriesRef.current?.setData(candles.map(toChartCandle))
    ;(seriesRef.current as any)?.setMarkers?.(markers as any)
    chartRef.current?.timeScale().fitContent()
    setSummary(data.summary ?? null)
    setStatus(`backtest done (${markers.length} entries)`)
  }

  useEffect(() => {
    // auto load initial
    if (seriesRef.current) loadCandles()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [symbol, timeframe, daysBack])

  const tfOptions: Timeframe[] = useMemo(() => ['1m', '5m', '15m', '1h', '4h', '1d'], [])

  return (
    <div className="wrap">
      <div className="topbar">
        <select value={symbol} onChange={(e) => setSymbol(e.target.value)}>
          {(symbols.length ? symbols : [symbol]).map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>

        <select value={timeframe} onChange={(e) => setTimeframe(e.target.value as Timeframe)}>
          {tfOptions.map((tf) => (
            <option key={tf} value={tf}>
              {tf}
            </option>
          ))}
        </select>

        <input
          type="number"
          min={1}
          max={3650}
          value={daysBack}
          onChange={(e) => setDaysBack(Number(e.target.value))}
          style={{ width: 110 }}
        />

        <button onClick={loadCandles}>Reload</button>
        <button onClick={runBacktest}>Backtest</button>

        <div className="stat">
          <div>{status}</div>
          {error ? <div style={{ color: '#ffca28' }}>{error}</div> : null}
          {summary ? (
            <div>
              trades={summary.trades} | winrate={summary.winrate.toFixed(1)}% | avgR={summary.avg_r.toFixed(2)}
            </div>
          ) : null}
        </div>
      </div>

      <div className="chart" ref={containerRef} />
    </div>
  )
}

