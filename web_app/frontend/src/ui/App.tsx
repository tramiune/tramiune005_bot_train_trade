import React, { useEffect, useMemo, useRef, useState } from 'react'
import {
  createChart,
  CrosshairMode,
  IChartApi,
  ISeriesApi,
  CandlestickSeries,
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

function apiBase() {
  const host = window.location.hostname || 'localhost'
  return `http://${host}:8000`
}

export function App() {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const seriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null)

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

      window.addEventListener('resize', resize)
      return () => {
        window.removeEventListener('resize', resize)
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

  const loadCandles = async () => {
    setStatus('loading candles...')
    setSummary(null)
    setError('')
    const url = new URL(`${apiBase()}/api/ohlcv`)
    url.searchParams.set('symbol', symbol)
    url.searchParams.set('timeframe', timeframe)
    url.searchParams.set('days_back', String(daysBack))
    url.searchParams.set('provider', 'ccxt')
    url.searchParams.set('exchange', 'binance')
    let data: any
    try {
      const res = await fetch(url.toString())
      data = await res.json()
    } catch (e: any) {
      setError(`Cannot reach backend at ${apiBase()} (ohlcv).`)
      setStatus('error')
      return
    }
    const candles: Candle[] = data.candles ?? []
    seriesRef.current?.setData(candles)
    seriesRef.current?.setMarkers([])
    chartRef.current?.timeScale().fitContent()
    setStatus(`loaded ${candles.length} candles`)
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
    seriesRef.current?.setData(candles)
    seriesRef.current?.setMarkers(markers as any)
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

