import React, { useEffect, useRef, useState } from 'react';
import { createChart, ColorType, CandlestickSeries, createSeriesMarkers, LineSeries } from 'lightweight-charts';
import type { IChartApi, ISeriesApi, LogicalRange } from 'lightweight-charts';
import { calculateNadarayaWatson, calculateSupertrend, detectStrategyTrades } from '../utils/indicators';
import { TradeZonesPrimitive } from '../utils/tradeZones';
import axios from 'axios';
import { Loader2, ArrowRightToLine } from 'lucide-react';

interface ChartWidgetProps {
    focusedTrade?: any;
    symbol: string;
}

const frontendCache: Record<string, any[]> = {};

const getInterval = (sym: string) => {
    if (sym === 'XRPUSDT') return '5m';
    if (sym === 'SOLUSDT') return '4h';
    if (sym === 'DOGEUSDT') return '3m';
    return '1h';
};

const ChartWidget: React.FC<ChartWidgetProps> = ({ symbol, focusedTrade }) => {
    const chartContainerRef = useRef<HTMLDivElement>(null);
    const chartRef = useRef<IChartApi | null>(null);
    const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
    
    // Strategy indicators (Nadaraya-Watson for XRP, Supertrend for SOL)
    const nwUpperSeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
    const nwLowerSeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
    const nwBaseSeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
    const stSeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
    
    const markersPrimitiveRef = useRef<any>(null);
    const zonesPrimitiveRef = useRef<TradeZonesPrimitive | null>(null);
    
    const candleDataRef = useRef<any[]>([]);
    const isFetchingRef = useRef<boolean>(false);
    const earliestTimeRef = useRef<number | null>(null);
    
    // Store active trade to redraw on pagination
    const activeTradeRef = useRef<any>(null);
    
    const [isBacktestLoading, setIsBacktestLoading] = useState<boolean>(true);
    const [lastUpdate, setLastUpdate] = useState<Date | null>(null);

    const updateStrategyIndicators = (candles: any[]) => {
        if (!candles || candles.length === 0) return;
        
        if (symbol === 'XRPUSDT') {
            const nw = calculateNadarayaWatson(candles, 8.0, 3.0);
            if (nwUpperSeriesRef.current) nwUpperSeriesRef.current.setData(nw.upper);
            if (nwLowerSeriesRef.current) nwLowerSeriesRef.current.setData(nw.lower);
            if (nwBaseSeriesRef.current) nwBaseSeriesRef.current.setData(nw.baseline);
            if (stSeriesRef.current) stSeriesRef.current.setData([]);
        } else if (symbol === 'SOLUSDT') {
            const st = calculateSupertrend(candles, 17, 4.4);
            if (stSeriesRef.current) stSeriesRef.current.setData(st.supertrend);
            if (nwUpperSeriesRef.current) nwUpperSeriesRef.current.setData([]);
            if (nwLowerSeriesRef.current) nwLowerSeriesRef.current.setData([]);
            if (nwBaseSeriesRef.current) nwBaseSeriesRef.current.setData([]);
        } else {
            if (nwUpperSeriesRef.current) nwUpperSeriesRef.current.setData([]);
            if (nwLowerSeriesRef.current) nwLowerSeriesRef.current.setData([]);
            if (nwBaseSeriesRef.current) nwBaseSeriesRef.current.setData([]);
            if (stSeriesRef.current) stSeriesRef.current.setData([]);
        }
    };

    
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
                markersPrimitiveRef.current = createSeriesMarkers(seriesRef.current, markers as any);
            } else {
                markersPrimitiveRef.current.setMarkers(markers as any);
            }
            
            if (activeTradeRef.current) {
                
            }
        }
    };

    const fetchKlines = async (endTime?: number) => {
        if (isFetchingRef.current) return;
        isFetchingRef.current = true;
        
        try {
            const limit = symbol === 'XRPUSDT' ? 1500 : 1000;
            let url = `/api/klines?symbol=${symbol}&interval=${getInterval(symbol)}&limit=${limit}`;
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
                    updateStrategyIndicators(candleDataRef.current);
                    const strategyTrades = detectStrategyTrades(candleDataRef.current, symbol);
                    frontendCache[symbol] = strategyTrades;
                    renderBacktest(strategyTrades, false);
                    reapplyMarkersAndLines();
                }
            } else {
                candleDataRef.current = formattedData;
                if (seriesRef.current) {
                    seriesRef.current.setData(candleDataRef.current);
                    setLastUpdate(new Date());
                    updateStrategyIndicators(candleDataRef.current);
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
        setIsBacktestLoading(true);
        try {
            // 1. Detect strategy trades directly from candle history
            const strategyTrades = detectStrategyTrades(candleDataRef.current, symbol);
            
            // 2. Fetch real trades from database for this coin
            const apiBase = symbol === 'SOLUSDT' ? '/api/sol' : '/api/xrp';
            const targetSymbol = symbol.replace('USDT', '/USDT');
            let dbTrades: any[] = [];
            try {
                const res = await axios.get(`${apiBase}/trades`);
                dbTrades = (res.data || [])
                    .filter((t: any) => t.symbol === targetSymbol)
                    .map((t: any) => {
                        const entryStr = t.entry_time?.endsWith('Z') ? t.entry_time : `${t.entry_time}Z`;
                        const exitStr = t.exit_time ? (t.exit_time.endsWith('Z') ? t.exit_time : `${t.exit_time}Z`) : undefined;
                        return {
                            time: new Date(entryStr).getTime() / 1000,
                            side: t.side,
                            entry: t.entry_price,
                            sl: t.stop_loss || (t.side === 'LONG' ? t.entry_price * 0.99 : t.entry_price * 1.01),
                            tp: t.take_profit || (t.side === 'LONG' ? t.entry_price * 1.15 : t.entry_price * 0.85),
                            exit_time: exitStr ? new Date(exitStr).getTime() / 1000 : undefined,
                            pnl: t.pnl,
                            balance_after: t.balance_after
                        };
                    });
            } catch (err) {
                console.error("Failed to fetch db trades", err);
            }
            
            // Merge strategy trades and DB trades smoothly without duplicates
            const allTrades = [...strategyTrades];
            for (const d of dbTrades) {
                const maxDiff = symbol === 'SOLUSDT' ? 14400 : 300;
                const idx = allTrades.findIndex(s => Math.abs(s.time - d.time) <= maxDiff && s.side === d.side);
                if (idx !== -1) {
                    allTrades[idx] = { ...allTrades[idx], ...d };
                } else {
                    allTrades.push(d);
                }
            }
            allTrades.sort((a: any, b: any) => a.time - b.time);
            
            frontendCache[symbol] = allTrades;
            renderBacktest(allTrades, false);
        } catch (e) {
            console.error("Failed to fetch backtest", e);
        } finally {
            setIsBacktestLoading(false);
        }
    };

    const renderBacktest = (trades: any[], shouldPan: boolean = true) => {
        zonesPrimitiveRef.current?.setTrades(trades);
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
                markersPrimitiveRef.current = createSeriesMarkers(seriesRef.current, markers as any);
            } else {
                markersPrimitiveRef.current.setMarkers(markers as any);
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
        
        activeTradeRef.current = trade;
        
        // Ensure data is loaded
        if (earliestTimeRef.current && trade.time < earliestTimeRef.current) {
            try {
                const endTimestamp = (trade.exit_time || trade.time) + (24 * 3600);
                const url = `/api/klines?symbol=${symbol.replace('/', '')}&interval=${getInterval(symbol)}&limit=1000&endTime=${endTimestamp * 1000}`;
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
                    updateStrategyIndicators(uniqueData);
                    if (frontendCache[symbol]) renderBacktest(frontendCache[symbol], false);
                    reapplyMarkersAndLines();
                }
            } catch (e) {
                console.error("Failed to fetch historical candles for trade", e);
            }
        }
        
        
        const padding = symbol === "XRPUSDT" ? 3600 : (symbol === "DOGEUSDT" ? 2 * 3600 : 72 * 3600);
        const endTime = trade.exit_time || (candleDataRef.current.length > 0 ? candleDataRef.current[candleDataRef.current.length - 1].time : trade.time + 3600);
        
        // Entry/SL/TP zones of ALL trades are painted by TradeZonesPrimitive; here we only highlight the selected one
        zonesPrimitiveRef.current?.setActive(trade.time);
        
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

        // Entry / TP / SL zones for every trade (painted only for the visible range)
        const zonesPrimitive = new TradeZonesPrimitive(() => candleDataRef.current);
        candlestickSeries.attachPrimitive(zonesPrimitive);
        zonesPrimitiveRef.current = zonesPrimitive;

        // Strategy Indicator: Nadaraya-Watson Envelope (XRP)
        const nwUpper = chart.addSeries(LineSeries, {
            color: '#f43f5e',
            lineWidth: 2,
            crosshairMarkerVisible: true,
            lastValueVisible: true,
            priceLineVisible: false,
            title: 'NW Upper'
        });
        nwUpperSeriesRef.current = nwUpper;
        
        const nwLower = chart.addSeries(LineSeries, {
            color: '#10b981',
            lineWidth: 2,
            crosshairMarkerVisible: true,
            lastValueVisible: true,
            priceLineVisible: false,
            title: 'NW Lower'
        });
        nwLowerSeriesRef.current = nwLower;
        
        const nwBase = chart.addSeries(LineSeries, {
            color: 'rgba(148, 163, 184, 0.4)',
            lineWidth: 1,
            lineStyle: 2,
            crosshairMarkerVisible: false,
            lastValueVisible: false,
            priceLineVisible: false,
            title: 'NW Base'
        });
        nwBaseSeriesRef.current = nwBase;
        
        // Strategy Indicator: Supertrend Line (SOL)
        const stSeries = chart.addSeries(LineSeries, {
            lineWidth: 2,
            crosshairMarkerVisible: true,
            lastValueVisible: true,
            priceLineVisible: false,
            title: 'Supertrend'
        });
        stSeriesRef.current = stSeries;
        
        
        
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
                    <h3 className="text-white font-semibold text-lg">{symbol.toUpperCase()} - {symbol === 'XRPUSDT' ? '5m (BẮT ĐÁY)' : (symbol === 'SOLUSDT' ? '4H (CƯỠI SÓNG)' : (symbol === 'DOGEUSDT' ? '3m' : '1H'))}</h3>
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
