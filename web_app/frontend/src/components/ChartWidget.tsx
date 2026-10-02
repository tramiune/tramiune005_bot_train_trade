import React, { useEffect, useRef, useState } from 'react';
import { createChart, ColorType, CandlestickSeries, createSeriesMarkers, BaselineSeries, LineSeries } from 'lightweight-charts';
import type { IChartApi, ISeriesApi, LogicalRange, IPriceLine } from 'lightweight-charts';
import { calculateEMA } from '../utils/indicators';
import axios from 'axios';
import { Loader2, ArrowRightToLine } from 'lucide-react';

interface ChartWidgetProps {
    focusedTrade?: any;
    symbol: string;
}

const frontendCache: Record<string, any[]> = {};

const ChartWidget: React.FC<ChartWidgetProps> = ({ symbol, focusedTrade }) => {
    const chartContainerRef = useRef<HTMLDivElement>(null);
    const chartRef = useRef<IChartApi | null>(null);
    const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
    const ema20SeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
    const ema200SeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
    
    // Price line references (changed to series references)
    const tpSeriesRef = useRef<any>(null);
    const tradeSeriesRef = useRef<any[]>([]);
    const markersPrimitiveRef = useRef<any>(null);
    
    const candleDataRef = useRef<any[]>([]);
    const isFetchingRef = useRef<boolean>(false);
    const earliestTimeRef = useRef<number | null>(null);
    
    // Store active trade to redraw on pagination
    const activeTradeRef = useRef<any>(null);
    
    const [backtestTrades, setBacktestTrades] = useState<any[]>([]);
    const [isBacktestLoading, setIsBacktestLoading] = useState<boolean>(true);
    const [activeTradeId, setActiveTradeId] = useState<number | null>(null);

    const renderVisibleTrades = (timeRange: any) => {
        if (!timeRange || !frontendCache[symbol] || !chartRef.current) return;
        
        const fromTime = timeRange.from;
        const toTime = timeRange.to;
        
        const visibleTrades = frontendCache[symbol].filter((trade: any) => {
             const endTime = trade.exit_time || trade.time;
             return trade.time <= toTime && endTime >= fromTime;
        });
        
        const currentTradeIds = tradeSeriesRef.current.map(s => s.tradeId).join(',');
        const newTradeIds = visibleTrades.map(t => t.time).join(',');
        
        if (currentTradeIds === newTradeIds) return;
        
        tradeSeriesRef.current.forEach(s => {
            try { chartRef.current?.removeSeries(s.tpSeries); } catch(e){}
            try { chartRef.current?.removeSeries(s.slSeries); } catch(e){}
        });
        tradeSeriesRef.current = [];
        
        visibleTrades.forEach((trade: any) => {
            const endTime = trade.exit_time || trade.time;
            const isLong = trade.side === 'LONG';
            
            const tpSeries = chartRef.current!.addSeries(BaselineSeries, {
                baseValue: { type: 'price', price: trade.entry },
                topFillColor1: isLong ? 'rgba(38, 166, 154, 0.35)' : 'rgba(0, 0, 0, 0)',
                topFillColor2: isLong ? 'rgba(38, 166, 154, 0.35)' : 'rgba(0, 0, 0, 0)',
                topLineColor: isLong ? '#26a69a' : 'rgba(0, 0, 0, 0)',
                bottomFillColor1: !isLong ? 'rgba(38, 166, 154, 0.35)' : 'rgba(0, 0, 0, 0)',
                bottomFillColor2: !isLong ? 'rgba(38, 166, 154, 0.35)' : 'rgba(0, 0, 0, 0)',
                bottomLineColor: !isLong ? '#26a69a' : 'rgba(0, 0, 0, 0)',
                lineWidth: 3,
                lineStyle: 0,
                lastValueVisible: false,
                priceLineVisible: false,
            });
            
            const slSeries = chartRef.current!.addSeries(BaselineSeries, {
                baseValue: { type: 'price', price: trade.entry },
                topFillColor1: !isLong ? 'rgba(239, 83, 80, 0.35)' : 'rgba(0, 0, 0, 0)',
                topFillColor2: !isLong ? 'rgba(239, 83, 80, 0.35)' : 'rgba(0, 0, 0, 0)',
                topLineColor: !isLong ? '#ef5350' : 'rgba(0, 0, 0, 0)',
                bottomFillColor1: isLong ? 'rgba(239, 83, 80, 0.35)' : 'rgba(0, 0, 0, 0)',
                bottomFillColor2: isLong ? 'rgba(239, 83, 80, 0.35)' : 'rgba(0, 0, 0, 0)',
                bottomLineColor: isLong ? '#ef5350' : 'rgba(0, 0, 0, 0)',
                lineWidth: 3,
                lineStyle: 0,
                lastValueVisible: false,
                priceLineVisible: false,
            });
            
            tpSeries.setData([
                { time: trade.time, value: trade.tp },
                { time: endTime, value: trade.tp }
            ]);
            
            slSeries.setData([
                { time: trade.time, value: trade.sl },
                { time: endTime, value: trade.sl }
            ]);
            
            tradeSeriesRef.current.push({
                tradeId: trade.time,
                tpSeries,
                slSeries
            });
        });
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
                
            }
        }
    };

    const fetchKlines = async (endTime?: number) => {
        if (isFetchingRef.current) return;
        isFetchingRef.current = true;
        
        try {
            let url = `http://${window.location.hostname}:8000/api/klines?symbol=${symbol}&interval=${symbol === 'DOGEUSDT' ? '3m' : '1h'}&limit=1000`;
            if (endTime) {
                url += `&endTime=${endTime * 1000}`;
            }
            
            const res = await axios.get(url);
            const data = res.data.data ? res.data.data : res.data;
            
            if (!data || data.length === 0) {
                isFetchingRef.current = false;
                return;
            }

            const formattedData = data;

            if (endTime) {
                const newData = [...formattedData, ...candleDataRef.current];
                const uniqueData = Array.from(new Map(newData.map(item => [item.time, item])).values());
                uniqueData.sort((a: any, b: any) => a.time - b.time);
                
                candleDataRef.current = uniqueData;
                if (seriesRef.current) {
                    seriesRef.current.setData(candleDataRef.current);
                    if (ema20SeriesRef.current) ema20SeriesRef.current.setData(calculateEMA(candleDataRef.current, 20));
                    if (ema200SeriesRef.current) ema200SeriesRef.current.setData(calculateEMA(candleDataRef.current, 200));
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
            
            earliestTimeRef.current = candleDataRef.current[0]?.time;
            
        } catch (error) {
            console.error("Failed to fetch klines:", error);
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
            const url = `http://${window.location.hostname}:8000/api/trades`;
            const res = await axios.get(url);
            
            // Filter by symbol
            const targetSymbol = symbol.replace('USDT', '/USDT');
            const symbolTrades = res.data.filter((t: any) => t.symbol === targetSymbol);
            
            const trades = symbolTrades.map((t: any) => ({
                time: new Date(t.entry_time).getTime() / 1000,
                side: t.side,
                entry: t.entry_price,
                sl: t.stop_loss || (t.side === 'LONG' ? t.entry_price * 0.85 : t.entry_price * 1.15),
                tp: t.take_profit || (t.side === 'LONG' ? t.entry_price * 1.05 : t.entry_price * 0.95),
                exit_time: t.exit_time ? new Date(t.exit_time).getTime() / 1000 : undefined,
                pnl: t.pnl,
                balance_after: t.balance_after
            }));
            
            // Sort trades by time just to be safe
            trades.sort((a: any, b: any) => a.time - b.time);
            
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
        if (!chartRef.current) return;
        setActiveTradeId(null);
        activeTradeRef.current = null;
        
        tradeSeriesRef.current.forEach(s => {
            try { chartRef.current?.removeSeries(s.tpSeries); } catch(e){}
            try { chartRef.current?.removeSeries(s.slSeries); } catch(e){}
        });
        tradeSeriesRef.current = [];
        
        chartRef.current.timeScale().scrollToRealTime();
        if (seriesRef.current) {
            seriesRef.current.priceScale().applyOptions({ autoScale: true });
        }
    };

    const handleTradeClick = async (trade: any) => {
        if (!chartRef.current) return;
        
        setActiveTradeId(trade.time);
        activeTradeRef.current = trade;
        
        // Ensure data is loaded
        if (earliestTimeRef.current && trade.time < earliestTimeRef.current) {
            try {
                const endTimestamp = (trade.exit_time || trade.time) + (24 * 3600);
                const url = `http://${window.location.hostname}:8000/api/klines?symbol=${symbol.replace('/', '')}&interval=${symbol === 'DOGEUSDT' ? '3m' : '1h'}&limit=1000&endTime=${endTimestamp * 1000}`;
                const res = await axios.get(url);
                const formatted = res.data.data ? res.data.data : res.data;
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
                }
            } catch (e) {
                console.error("Failed to fetch historical candles for trade", e);
            }
        }
        
        
        const padding = symbol === "DOGEUSDT" ? 2 * 3600 : 72 * 3600;
        const endTime = trade.exit_time || trade.time;
        chartRef.current.timeScale().setVisibleRange({
            from: (trade.time - padding) as any,
            to: (endTime + padding) as any
        });
        
        if (seriesRef.current) {
            seriesRef.current.priceScale().applyOptions({ autoScale: false });
            setTimeout(() => {
                if (seriesRef.current) seriesRef.current.priceScale().applyOptions({ autoScale: true });
            }, 50);
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
                tickMarkFormatter: (time: any, tickMarkType: any, locale: string) => {
                    const date = new Date(time * 1000);
                    if (tickMarkType === 0) return date.getFullYear().toString();
                    if (tickMarkType === 1) return date.toLocaleString(locale, { month: 'short' });
                    if (tickMarkType === 2) return date.getDate().toString();
                    return date.toLocaleTimeString(locale, { hour: '2-digit', minute: '2-digit', hour12: false });
                }
            },
            localization: {
                timeFormatter: (time: any) => {
                    const date = new Date(time * 1000);
                    return date.toLocaleString();
                }
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

        const wsUrl = `wss://stream.binance.com:9443/ws/${symbol.toLowerCase()}@kline_${symbol === 'DOGEUSDT' ? '3m' : '1h'}`;
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

        const onVisibleTimeRangeChanged = (timeRange: any) => {
            renderVisibleTrades(timeRange);
        };

        chart.timeScale().subscribeVisibleTimeRangeChange(onVisibleTimeRangeChanged);

        return () => {
            ws.close();
            chart.timeScale().unsubscribeVisibleLogicalRangeChange(onVisibleLogicalRangeChanged);
            chart.timeScale().unsubscribeVisibleTimeRangeChange(onVisibleTimeRangeChanged);
            chart.remove();
        };
    }, [symbol]);


    useEffect(() => {
        if (focusedTrade && chartRef.current) {
            const mappedTrade = {
                time: new Date(focusedTrade.entry_time).getTime() / 1000,
                exit_time: focusedTrade.exit_time ? new Date(focusedTrade.exit_time).getTime() / 1000 : undefined,
                side: focusedTrade.side,
                entry: focusedTrade.entry_price,
                sl: focusedTrade.stop_loss,
                tp: focusedTrade.take_profit
            };
            handleTradeClick(mappedTrade);
        }
    }, [focusedTrade]);

    return (
        <div className="w-full flex flex-col space-y-4">
            <div className="w-full bg-[#1E222D] rounded-lg overflow-hidden border border-gray-700 shadow-lg flex flex-col relative">
                <div className="p-4 border-b border-gray-700 flex justify-between items-center">
                    <h3 className="text-white font-semibold text-lg">{symbol.toUpperCase()} - {symbol === 'DOGEUSDT' ? '3m (DEGEN MODE)' : '1H'}</h3>
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
                                <th className="px-4 py-2">{symbol === 'DOGEUSDT' ? 'PnL' : 'RR'}</th>
                                {symbol === 'DOGEUSDT' && <th className="px-4 py-2 text-yellow-400">Balance</th>}
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
                                    <td className={"px-4 py-2 font-mono " + (symbol === 'DOGEUSDT' ? (trade.pnl > 0 ? "text-green-400" : "text-red-400") : "text-blue-300")}>
                                        {symbol === 'DOGEUSDT' ? (trade.pnl > 0 ? "+" : "") + trade.pnl.toFixed(2) + "$" : ((trade.tp - trade.entry) / (trade.entry - trade.sl)).toFixed(1)}
                                    </td>
                                    {symbol === 'DOGEUSDT' && <td className="px-4 py-2 font-mono text-yellow-400 font-bold">${trade.balance_after?.toFixed(2)}</td>}
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
