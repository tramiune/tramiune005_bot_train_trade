import React, { useEffect, useRef, useState } from 'react';
import { createChart, ColorType, CandlestickSeries, createSeriesMarkers, BaselineSeries, LineSeries } from 'lightweight-charts';
import type { IChartApi, ISeriesApi, LogicalRange, IPriceLine } from 'lightweight-charts';
import { calculateEMA } from '../utils/indicators';
import axios from 'axios';
import { Loader2, ArrowRightToLine } from 'lucide-react';

interface ChartWidgetProps {
    symbol: string;
}

const frontendCache: Record<string, any[]> = {};

const ChartWidget: React.FC<ChartWidgetProps> = ({ symbol }) => {
    const chartContainerRef = useRef<HTMLDivElement>(null);
    const chartRef = useRef<IChartApi | null>(null);
    const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
    const ema20SeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
    const ema200SeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
    
    // Price line references (changed to series references)
    const tpSeriesRef = useRef<any>(null);
    const slSeriesRef = useRef<any>(null);
    const markersPrimitiveRef = useRef<any>(null);
    
    const candleDataRef = useRef<any[]>([]);
    const isFetchingRef = useRef<boolean>(false);
    const earliestTimeRef = useRef<number | null>(null);
    
    // Store active trade to redraw on pagination
    const activeTradeRef = useRef<any>(null);
    
    const [backtestTrades, setBacktestTrades] = useState<any[]>([]);
    const [isBacktestLoading, setIsBacktestLoading] = useState<boolean>(true);
    const [activeTradeId, setActiveTradeId] = useState<number | null>(null);

    const drawTradeLines = (trade: any) => {
        if (!chartRef.current || !trade) return;
        
        // Remove old series if they exist
        if (tpSeriesRef.current) {
            try { chartRef.current.removeSeries(tpSeriesRef.current); } catch(e){}
            tpSeriesRef.current = null;
        }
        if (slSeriesRef.current) {
            try { chartRef.current.removeSeries(slSeriesRef.current); } catch(e){}
            slSeriesRef.current = null;
        }
        
        const endTime = trade.exit_time || trade.time;
        // Create TP Baseline Series
        tpSeriesRef.current = chartRef.current.addSeries(BaselineSeries, {
            baseValue: { type: 'price', price: trade.entry },
            topFillColor1: 'rgba(38, 166, 154, 0.35)',
            topFillColor2: 'rgba(38, 166, 154, 0.35)',
            topLineColor: '#26a69a',
            bottomFillColor1: 'rgba(0, 0, 0, 0)',
            bottomFillColor2: 'rgba(0, 0, 0, 0)',
            bottomLineColor: 'rgba(0, 0, 0, 0)',
            lineWidth: 3,
            lineStyle: 0,
            lastValueVisible: false,
            priceLineVisible: false,
        });
        
        // Create SL Baseline Series
        slSeriesRef.current = chartRef.current.addSeries(BaselineSeries, {
            baseValue: { type: 'price', price: trade.entry },
            topFillColor1: 'rgba(0, 0, 0, 0)',
            topFillColor2: 'rgba(0, 0, 0, 0)',
            topLineColor: 'rgba(0, 0, 0, 0)',
            bottomFillColor1: 'rgba(239, 83, 80, 0.35)',
            bottomFillColor2: 'rgba(239, 83, 80, 0.35)',
            bottomLineColor: '#ef5350',
            lineWidth: 3,
            lineStyle: 0,
            lastValueVisible: false,
            priceLineVisible: false,
        });
        
        tpSeriesRef.current.setData([
            { time: trade.time, value: trade.tp },
            { time: endTime, value: trade.tp }
        ]);
        
        slSeriesRef.current.setData([
            { time: trade.time, value: trade.sl },
            { time: endTime, value: trade.sl }
        ]);
    };

    const reapplyMarkersAndLines = () => {
        if (!seriesRef.current || !frontendCache[symbol]) return;
        
        const trades = frontendCache[symbol];
        if (trades.length > 0) {
            const markers = trades.map((t: any) => ({
                time: t.time,
                position: t.side === 'LONG' ? 'belowBar' : 'aboveBar',
                color: t.side === 'LONG' ? '#22c55e' : '#ef4444',
                shape: t.side === 'LONG' ? 'arrowUp' : 'arrowDown',
                text: `${t.side}`,
                size: 2
            }));
            
            if (!markersPrimitiveRef.current) {
                markersPrimitiveRef.current = createSeriesMarkers(seriesRef.current, markers);
            } else {
                markersPrimitiveRef.current.setMarkers(markers);
            }
            
            if (activeTradeRef.current) {
                drawTradeLines(activeTradeRef.current);
            }
        }
    };

    const fetchKlines = async (endTime?: number) => {
        if (isFetchingRef.current) return;
        isFetchingRef.current = true;
        
        try {
            let url = `https://fapi.binance.com/fapi/v1/klines?symbol=${symbol}&interval=1h&limit=1000`;
            if (endTime) {
                url += `&endTime=${endTime}`;
            }
            
            const res = await axios.get(url);
            const data = res.data;
            
            if (data.length === 0) {
                isFetchingRef.current = false;
                return;
            }

            const formattedData = data.map((d: any) => ({
                time: d[0] / 1000,
                open: parseFloat(d[1]),
                high: parseFloat(d[2]),
                low: parseFloat(d[3]),
                close: parseFloat(d[4]),
            }));

            if (endTime) {
                const newBatch = formattedData.filter((f: any) => !candleDataRef.current.find((c: any) => c.time === f.time));
                candleDataRef.current = [...newBatch, ...candleDataRef.current];
                if (seriesRef.current) {
                    seriesRef.current.setData(candleDataRef.current);
                    if (ema20SeriesRef.current) ema20SeriesRef.current.setData(calculateEMA(candleDataRef.current, 20));
                    if (ema200SeriesRef.current) ema200SeriesRef.current.setData(calculateEMA(candleDataRef.current, 200));
                    // REDRAW MARKERS & LINES AFTER SETDATA WIPES THEM
                    reapplyMarkersAndLines();
                }
            } else {
                candleDataRef.current = formattedData;
                if (seriesRef.current) {
                    seriesRef.current.setData(candleDataRef.current);
                    if (ema20SeriesRef.current) ema20SeriesRef.current.setData(calculateEMA(candleDataRef.current, 20));
                    if (ema200SeriesRef.current) ema200SeriesRef.current.setData(calculateEMA(candleDataRef.current, 200));
                }
            }

            earliestTimeRef.current = data[0][0] - 1;

        } catch (e) {
            console.error("Failed to fetch klines", e);
        } finally {
            isFetchingRef.current = false;
        }
    };

    const fetchBacktest = async () => {
        if (frontendCache[symbol]) {
            renderBacktest(frontendCache[symbol]);
            setIsBacktestLoading(false);
            return;
        }

        setIsBacktestLoading(true);
        try {
            const res = await axios.get(`http://${window.location.hostname}:8000/api/backtest?symbol=${symbol.replace('USDT', '/USDT')}`);
            const trades = res.data;
            
            frontendCache[symbol] = trades;
            renderBacktest(trades);
        } catch (e) {
            console.error("Failed to fetch backtest", e);
        } finally {
            setIsBacktestLoading(false);
        }
    };

    const renderBacktest = (trades: any[]) => {
        setBacktestTrades(trades);
        if (seriesRef.current && trades.length > 0) {
            const markers = trades.map((t: any) => ({
                time: t.time,
                position: t.side === 'LONG' ? 'belowBar' : 'aboveBar',
                color: t.side === 'LONG' ? '#22c55e' : '#ef4444',
                shape: t.side === 'LONG' ? 'arrowUp' : 'arrowDown',
                text: `${t.side}`,
                size: 2
            }));
            
            if (!markersPrimitiveRef.current) {
                markersPrimitiveRef.current = createSeriesMarkers(seriesRef.current, markers);
            } else {
                markersPrimitiveRef.current.setMarkers(markers);
            }
            
            // Use handleTradeClick to properly zoom and fetch historical candles if necessary
            const latest = trades[trades.length - 1];
            setTimeout(() => {
                handleTradeClick(latest);
            }, 500);
        }
    };

    const handleGoToRealTime = () => {
        if (!chartRef.current || candleDataRef.current.length === 0) return;
        setActiveTradeId(null);
        if (tpSeriesRef.current) {
            try { chartRef.current.removeSeries(tpSeriesRef.current); } catch(e){}
            tpSeriesRef.current = null;
        }
        if (slSeriesRef.current) {
            try { chartRef.current.removeSeries(slSeriesRef.current); } catch(e){}
            slSeriesRef.current = null;
        }
        const lastCandle = candleDataRef.current[candleDataRef.current.length - 1];
        chartRef.current.timeScale().scrollToRealTime();
        if (seriesRef.current) {
            seriesRef.current.priceScale().applyOptions({ autoScale: true });
        }
    };

    const handleTradeClick = async (trade: any) => {
        if (!chartRef.current) return;
        
        setActiveTradeId(trade.time);
        activeTradeRef.current = trade;
        drawTradeLines(trade);
        
        const padding = 72 * 3600;
        const endTime = trade.exit_time || trade.time;
        chartRef.current.timeScale().setVisibleRange({
            from: (trade.time - padding) as any,
            to: (endTime + padding) as any
        });
        
        // Temporarily reset autoscale so it fits the price lines
        if (seriesRef.current) {
            seriesRef.current.priceScale().applyOptions({ autoScale: false });
            setTimeout(() => {
                if (seriesRef.current) seriesRef.current.priceScale().applyOptions({ autoScale: true });
            }, 50);
        }

        // Fetch candles around this trade if we don't have them!
        if (earliestTimeRef.current && trade.time < earliestTimeRef.current) {
            try {
                // Fetch 1000 candles ending shortly after the trade
                const endTimestamp = (trade.exit_time || trade.time) + (7 * 24 * 3600);
                const url = `https://api.binance.com/api/v3/klines?symbol=${symbol.replace('/', '')}&interval=1h&limit=1000&endTime=${endTimestamp * 1000}`;
                const res = await axios.get(url);
                const formatted = res.data.map((d: any) => ({
                    time: d[0] / 1000,
                    open: parseFloat(d[1]),
                    high: parseFloat(d[2]),
                    low: parseFloat(d[3]),
                    close: parseFloat(d[4]),
                }));
                // Sort and deduplicate with existing data
                const newData = [...formatted, ...candleDataRef.current];
                const uniqueData = Array.from(new Map(newData.map(item => [item.time, item])).values());
                uniqueData.sort((a: any, b: any) => a.time - b.time);
                
                candleDataRef.current = uniqueData;
                earliestTimeRef.current = uniqueData[0].time;
                if (seriesRef.current) {
                    seriesRef.current.setData(uniqueData);
                    if (ema20SeriesRef.current) ema20SeriesRef.current.setData(calculateEMA(uniqueData, 20));
                    if (ema200SeriesRef.current) ema200SeriesRef.current.setData(calculateEMA(uniqueData, 200));
                    reapplyMarkersAndLines();
                    // Set visible range again after data is loaded
                    chartRef.current.timeScale().setVisibleRange({
                        from: (trade.time - padding) as any,
                        to: (endTime + padding) as any
                    });
                }
            } catch (e) {
                console.error("Failed to fetch historical candles for trade", e);
            }
        }
    };

    useEffect(() => {
        candleDataRef.current = [];
        earliestTimeRef.current = null;
        isFetchingRef.current = false;
        
        if (!frontendCache[symbol]) {
             setBacktestTrades([]);
             // Only show the loading screen if we actually need to fetch it
             setIsBacktestLoading(true);
        }

        if (!chartContainerRef.current) return;
        
        const chart = createChart(chartContainerRef.current, {
            layout: {
                background: { type: ColorType.Solid, color: '#1E222D' },
                textColor: '#D9D9D9',
            },
            grid: {
                vertLines: { color: '#2B2B43' },
                horzLines: { color: '#2B2B43' },
            },
            autoSize: true,
            timeScale: {
                timeVisible: true,
                secondsVisible: false,
            },
        });
        chartRef.current = chart;

        const candlestickSeries = chart.addSeries(CandlestickSeries, {
            upColor: '#26a69a',
            downColor: '#ef5350',
            borderVisible: false,
            wickUpColor: '#26a69a',
            wickDownColor: '#ef5350',
            autoscaleInfoProvider: (original: () => any) => {
                const res = original();
                if (res !== null && activeTradeRef.current) {
                    if (res.priceRange) {
                        res.priceRange.minValue = Math.min(res.priceRange.minValue, activeTradeRef.current.sl, activeTradeRef.current.tp);
                        res.priceRange.maxValue = Math.max(res.priceRange.maxValue, activeTradeRef.current.sl, activeTradeRef.current.tp);
                    }
                }
                return res;
            }
        });
        seriesRef.current = candlestickSeries;
        
        ema20SeriesRef.current = chart.addSeries(LineSeries, {
            color: '#2962FF',
            lineWidth: 2,
            crosshairMarkerVisible: false,
            lastValueVisible: false,
            priceLineVisible: false,
        });
        
        ema200SeriesRef.current = chart.addSeries(LineSeries, {
            color: '#9C27B0',
            lineWidth: 2,
            crosshairMarkerVisible: false,
            lastValueVisible: false,
            priceLineVisible: false,
        });
        
        // Reset refs
        markersPrimitiveRef.current = null;
        activeTradeRef.current = null;
        
        fetchKlines().then(() => {
            fetchBacktest();
        });

        const wsUrl = `wss://stream.binance.com:9443/ws/${symbol.toLowerCase()}@kline_1h`;
        const ws = new WebSocket(wsUrl);

        ws.onmessage = (event) => {
            const message = JSON.parse(event.data);
            const kline = message.k;
            const newTick = {
                time: (kline.t / 1000) as any,
                open: parseFloat(kline.o),
                high: parseFloat(kline.h),
                low: parseFloat(kline.l),
                close: parseFloat(kline.c),
            };
            
            candlestickSeries.update(newTick);
            
            if (candleDataRef.current.length > 0) {
                const lastIdx = candleDataRef.current.length - 1;
                if (candleDataRef.current[lastIdx].time === newTick.time) {
                    candleDataRef.current[lastIdx] = newTick;
                } else if (newTick.time > candleDataRef.current[lastIdx].time) {
                    candleDataRef.current.push(newTick);
                }
            }
        };

        const onVisibleLogicalRangeChanged = (logicalRange: LogicalRange | null) => {
            if (!logicalRange) return;
            if (logicalRange.from < 10) {
                if (earliestTimeRef.current) {
                    fetchKlines(earliestTimeRef.current);
                }
            }
        };

        chart.timeScale().subscribeVisibleLogicalRangeChange(onVisibleLogicalRangeChanged);

        return () => {
            ws.close();
            chart.timeScale().unsubscribeVisibleLogicalRangeChange(onVisibleLogicalRangeChanged);
            chart.remove();
        };
    }, [symbol]);

    return (
        <div className="w-full flex flex-col space-y-4">
            <div className="w-full bg-[#1E222D] rounded-lg overflow-hidden border border-gray-700 shadow-lg flex flex-col relative">
                <div className="p-4 border-b border-gray-700 flex justify-between items-center">
                    <h3 className="text-white font-semibold text-lg">{symbol.toUpperCase()} - 1H</h3>
                    <span className="flex items-center text-xs text-green-400">
                        <span className="w-2 h-2 rounded-full bg-green-400 mr-2 animate-pulse"></span>
                        Live + Backtest Active
                    </span>
                </div>
                
            <div className="relative w-full h-[400px]" style={{ minHeight: '400px' }}>
                <button 
                    onClick={handleGoToRealTime}
                    className="absolute bottom-6 right-6 z-10 bg-slate-800/80 hover:bg-slate-700 text-slate-300 p-3 rounded-full shadow-lg backdrop-blur border border-slate-700 transition-colors"
                    title="Trở về thời gian thực"
                >
                    <ArrowRightToLine size={20} />
                </button>
                <div ref={chartContainerRef} className="w-full h-full" />
            </div>                
                {isBacktestLoading && (
                    <div className="absolute inset-0 bg-black/80 flex flex-col items-center justify-center z-10 backdrop-blur-sm">
                        <Loader2 className="w-12 h-12 text-blue-500 animate-spin mb-4" />
                        <h3 className="text-white font-bold text-lg mb-2">Syncing History...</h3>
                        <p className="text-gray-400 text-sm">Please wait while we connect to the engine</p>
                    </div>
                )}
            </div>
            
            {!isBacktestLoading && backtestTrades.length > 0 && (
                <div className="bg-gray-800 rounded-lg p-4 border border-gray-700 shadow-lg max-h-[300px] overflow-y-auto">
                    <h4 className="text-white font-bold mb-3 flex items-center justify-between">
                        <span>Historical Signals (Click to view on chart)</span>
                        <span className="text-xs bg-blue-900 text-blue-300 px-2 py-1 rounded-full border border-blue-500">
                            Found {backtestTrades.length} trades in 4 years
                        </span>
                    </h4>
                    <table className="w-full text-left text-sm text-gray-400">
                        <thead className="text-xs text-gray-400 uppercase bg-gray-700 sticky top-0 z-10">
                            <tr>
                                <th className="px-4 py-2">Date</th>
                                <th className="px-4 py-2">Entry</th>
                                <th className="px-4 py-2">SL</th>
                                <th className="px-4 py-2">TP</th>
                                <th className="px-4 py-2">RR</th>
                            </tr>
                        </thead>
                        <tbody>
                            {backtestTrades.slice().reverse().map((trade, idx) => (
                                <tr 
                                    key={idx} 
                                    onClick={() => handleTradeClick(trade)}
                                    className={`border-b border-gray-700 cursor-pointer transition-colors ${
                                        activeTradeId === trade.time ? 'bg-blue-900/60' : 'hover:bg-blue-900/40'
                                    }`}
                                >
                                    <td className="px-4 py-2 flex items-center">
                                        {activeTradeId === trade.time && <span className="mr-2 text-blue-400">▶</span>}
                                        {new Date(trade.time * 1000).toLocaleString()}
                                    </td>
                                    <td className="px-4 py-2 text-blue-400 font-bold">${trade.entry.toFixed(4)}</td>
                                    <td className="px-4 py-2 text-red-400">${trade.sl.toFixed(4)}</td>
                                    <td className="px-4 py-2 text-green-400">${trade.tp.toFixed(4)}</td>
                                    <td className="px-4 py-2 font-mono text-blue-300">
                                        {((trade.tp - trade.entry) / (trade.entry - trade.sl)).toFixed(1)}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
};

export default ChartWidget;
