import React, { useEffect, useRef, useState } from 'react';
import { createChart, ColorType, CandlestickSeries, createSeriesMarkers, BaselineSeries, LineSeries } from 'lightweight-charts';
import type { IChartApi, ISeriesApi, LogicalRange, IPriceLine } from 'lightweight-charts';
import { calculateBB, calculateKC } from '../utils/indicators';
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
    const bbUpperSeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
    const bbLowerSeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
    const kcUpperSeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
    const kcLowerSeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
    const midSeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
    
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
    const [lastUpdate, setLastUpdate] = useState<Date | null>(null);

    
    const reapplyMarkersAndLines = () => {
        if (!seriesRef.current || !frontendCache[symbol]) return;
        
        const trades = frontendCache[symbol];
        if (trades.length > 0) {
            const firstCandleTime = candleDataRef.current.length > 0 ? candleDataRef.current[0].time : 0;
            const validTrades = trades.filter(t => t.time >= firstCandleTime);
            const markers = validTrades.map((t: any) => ({
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
                    const bbData = calculateBB(candleDataRef.current, 20, 2.0);
                    const kcData = calculateKC(candleDataRef.current, 20, 1.5);
                    if (bbUpperSeriesRef.current) bbUpperSeriesRef.current.setData(bbData.upper);
                    if (bbLowerSeriesRef.current) bbLowerSeriesRef.current.setData(bbData.lower);
                    if (kcUpperSeriesRef.current) kcUpperSeriesRef.current.setData(kcData.upper);
                    if (kcLowerSeriesRef.current) kcLowerSeriesRef.current.setData(kcData.lower);
                    if (midSeriesRef.current) midSeriesRef.current.setData(bbData.mid);
                    if (frontendCache[symbol]) renderBacktest(frontendCache[symbol], false);
                    reapplyMarkersAndLines();
                }
            } else {
                candleDataRef.current = formattedData;
                if (seriesRef.current) {
                    seriesRef.current.setData(candleDataRef.current);
                    setLastUpdate(new Date());
                    const bbData = calculateBB(candleDataRef.current, 20, 2.0);
                    const kcData = calculateKC(candleDataRef.current, 20, 1.5);
                    if (bbUpperSeriesRef.current) bbUpperSeriesRef.current.setData(bbData.upper);
                    if (bbLowerSeriesRef.current) bbLowerSeriesRef.current.setData(bbData.lower);
                    if (kcUpperSeriesRef.current) kcUpperSeriesRef.current.setData(kcData.upper);
                    if (kcLowerSeriesRef.current) kcLowerSeriesRef.current.setData(kcData.lower);
                    if (midSeriesRef.current) midSeriesRef.current.setData(bbData.mid);
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
        // Show cached trades instantly, but ALWAYS refetch so new trades appear without a page reload
        const hadCache = !!frontendCache[symbol];
        if (hadCache) {
            renderBacktest(frontendCache[symbol], false);
            setIsBacktestLoading(false);
        } else {
            setIsBacktestLoading(true);
        }
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
            
            const previousCount = hadCache ? frontendCache[symbol].length : 0;
            frontendCache[symbol] = trades;
            // Pan to the latest trade on first load, or when a brand-new trade just appeared
            renderBacktest(trades, !hadCache || trades.length > previousCount);
        } catch (e) {
            console.error("Failed to fetch backtest", e);
        } finally {
            setIsBacktestLoading(false);
        }
    };

    const renderBacktest = (trades: any[], shouldPan: boolean = true) => {
        setBacktestTrades(trades);
        if (seriesRef.current && trades.length > 0) {
            const firstCandleTime = candleDataRef.current.length > 0 ? candleDataRef.current[0].time : 0;
            const validTrades = trades.filter(t => t.time >= firstCandleTime);
            const markers = validTrades.map((t: any) => ({
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
            
            if (shouldPan) {
                const latest = trades[trades.length - 1];
                setTimeout(() => {
                    handleTradeClick(latest);
                }, 50);
            }
        }
    };

    const handleGoToRealTime = () => {
        if (!chartRef.current) return;
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
                    setLastUpdate(new Date());
                    const bbData = calculateBB(uniqueData, 20, 2.0);
                    const kcData = calculateKC(uniqueData, 20, 1.5);
                    if (bbUpperSeriesRef.current) bbUpperSeriesRef.current.setData(bbData.upper);
                    if (bbLowerSeriesRef.current) bbLowerSeriesRef.current.setData(bbData.lower);
                    if (kcUpperSeriesRef.current) kcUpperSeriesRef.current.setData(kcData.upper);
                    if (kcLowerSeriesRef.current) kcLowerSeriesRef.current.setData(kcData.lower);
                    if (midSeriesRef.current) midSeriesRef.current.setData(bbData.mid);
                    if (frontendCache[symbol]) renderBacktest(frontendCache[symbol], false);
                    reapplyMarkersAndLines();
                }
            } catch (e) {
                console.error("Failed to fetch historical candles for trade", e);
            }
        }
        
        
        const padding = symbol === "DOGEUSDT" ? 2 * 3600 : 72 * 3600;
        const endTime = trade.exit_time || (candleDataRef.current.length > 0 ? candleDataRef.current[candleDataRef.current.length - 1].time : trade.time + 3600);
        
        // Remove old SL/TP boxes
        tradeSeriesRef.current.forEach(s => {
            try { chartRef.current?.removeSeries(s.tpSeries); } catch(e){}
            try { chartRef.current?.removeSeries(s.slSeries); } catch(e){}
        });
        tradeSeriesRef.current = [];
        
        // Draw new SL/TP box for this trade only
        const isLong = trade.side === 'LONG';
        const tpSeries = chartRef.current.addSeries(BaselineSeries, {
            baseValue: { type: 'price', price: trade.entry },
            topFillColor1: isLong ? 'rgba(38, 166, 154, 0.12)' : 'rgba(0, 0, 0, 0)',
            topFillColor2: isLong ? 'rgba(38, 166, 154, 0.12)' : 'rgba(0, 0, 0, 0)',
            topLineColor: isLong ? '#26a69a' : 'rgba(0, 0, 0, 0)',
            bottomFillColor1: !isLong ? 'rgba(38, 166, 154, 0.12)' : 'rgba(0, 0, 0, 0)',
            bottomFillColor2: !isLong ? 'rgba(38, 166, 154, 0.12)' : 'rgba(0, 0, 0, 0)',
            bottomLineColor: !isLong ? '#26a69a' : 'rgba(0, 0, 0, 0)',
            lineWidth: 1,
            priceLineVisible: false,
            lastValueVisible: false,
            crosshairMarkerVisible: false
        });
        
        const slSeries = chartRef.current.addSeries(BaselineSeries, {
            baseValue: { type: 'price', price: trade.entry },
            topFillColor1: !isLong ? 'rgba(239, 83, 80, 0.12)' : 'rgba(0, 0, 0, 0)',
            topFillColor2: !isLong ? 'rgba(239, 83, 80, 0.12)' : 'rgba(0, 0, 0, 0)',
            topLineColor: !isLong ? '#ef5350' : 'rgba(0, 0, 0, 0)',
            bottomFillColor1: isLong ? 'rgba(239, 83, 80, 0.12)' : 'rgba(0, 0, 0, 0)',
            bottomFillColor2: isLong ? 'rgba(239, 83, 80, 0.12)' : 'rgba(0, 0, 0, 0)',
            bottomLineColor: isLong ? '#ef5350' : 'rgba(0, 0, 0, 0)',
            lineWidth: 1,
            priceLineVisible: false,
            lastValueVisible: false,
            crosshairMarkerVisible: false
        });
        
        const endPad = endTime + 180;
        tpSeries.setData([
            { time: trade.time, value: trade.entry },
            { time: trade.time + 60, value: trade.tp },
            { time: endPad, value: trade.tp }
        ]);
        slSeries.setData([
            { time: trade.time, value: trade.entry },
            { time: trade.time + 60, value: trade.sl },
            { time: endPad, value: trade.sl }
        ]);
        
        tradeSeriesRef.current = [{ tpSeries, slSeries, tradeId: trade.time }];
        
        chartRef.current.timeScale().setVisibleRange({
            from: (trade.time - padding) as any,
            to: (endTime + padding) as any
        });
        
        try {
            if (seriesRef.current && candleDataRef.current && candleDataRef.current.length > 0) {
                seriesRef.current.priceScale().applyOptions({ autoScale: false });
                setTimeout(() => {
                    try {
                        if (seriesRef.current) seriesRef.current.priceScale().applyOptions({ autoScale: true });
                    } catch(e) {}
                }, 50);
            }
        } catch (e) {
            console.warn("Could not apply price scale", e);
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
            priceFormat: {
                type: 'price',
                precision: 5,
                minMove: 0.00001,
            },
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

        // Keltner Channel
        const kcUpper = chart.addSeries(LineSeries, { color: 'rgba(255, 152, 0, 0.4)', lineWidth: 1, lineStyle: 2, crosshairMarkerVisible: false, lastValueVisible: false, priceLineVisible: false });
        kcUpperSeriesRef.current = kcUpper;
        
        const kcLower = chart.addSeries(LineSeries, { color: 'rgba(255, 152, 0, 0.4)', lineWidth: 1, lineStyle: 2, crosshairMarkerVisible: false, lastValueVisible: false, priceLineVisible: false });
        kcLowerSeriesRef.current = kcLower;
        
        // Bollinger Bands
        const bbUpper = chart.addSeries(LineSeries, { color: 'rgba(33, 150, 243, 0.8)', lineWidth: 2, crosshairMarkerVisible: false, lastValueVisible: false, priceLineVisible: false });
        bbUpperSeriesRef.current = bbUpper;
        
        const bbLower = chart.addSeries(LineSeries, { color: 'rgba(33, 150, 243, 0.8)', lineWidth: 2, crosshairMarkerVisible: false, lastValueVisible: false, priceLineVisible: false });
        bbLowerSeriesRef.current = bbLower;
        
        // Mid Line (SMA 20)
        const mid = chart.addSeries(LineSeries, { color: 'rgba(255, 255, 255, 0.5)', lineWidth: 1, crosshairMarkerVisible: false, lastValueVisible: false, priceLineVisible: false });
        midSeriesRef.current = mid;
        
        
        
        // Reset refs
        markersPrimitiveRef.current = null;
        activeTradeRef.current = null;
        
        fetchKlines().then(() => {
            fetchBacktest();
        });
        
        // Poll backend for updates (candle close & new trades) every 60s
        const intervalId = setInterval(() => {
            fetchKlines().then(() => {
                fetchBacktest();
            });
        }, 60000);

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
            clearInterval(intervalId);
            chart.timeScale().unsubscribeVisibleLogicalRangeChange(onVisibleLogicalRangeChanged);
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
                    <span className={`flex items-center text-xs ${lastUpdate && (new Date().getTime() - lastUpdate.getTime() < 10000) ? 'text-green-400' : 'text-orange-400'}`}>
                        <span className={`w-2 h-2 rounded-full mr-2 ${lastUpdate && (new Date().getTime() - lastUpdate.getTime() < 10000) ? 'bg-green-400 animate-pulse' : 'bg-orange-400'}`}></span>
                        {lastUpdate ? `Last tick: ${lastUpdate.toLocaleTimeString()}` : 'Connecting...'}
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
            
            
        </div>
    );
};

export default ChartWidget;
