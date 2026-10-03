import re

with open("components/ChartWidget.tsx", "r") as f:
    content = f.read()

# 1. Remove renderVisibleTrades completely
content = re.sub(r'const renderVisibleTrades = \(timeRange: any\) => \{.*?\n    \};\n', '', content, flags=re.DOTALL)

# 2. Remove event listeners in useEffect
content = content.replace("chart.timeScale().subscribeVisibleTimeRangeChange(onVisibleTimeRangeChanged);", "")
content = content.replace("chart.timeScale().unsubscribeVisibleTimeRangeChange(onVisibleTimeRangeChanged);", "")

# 3. Remove onVisibleTimeRangeChanged definition
content = re.sub(r'const onVisibleTimeRangeChanged = \(timeRange: any\) => \{.*?\n        \};\n', '', content, flags=re.DOTALL)

# 4. In handleGoToRealTime, remove the old tradeSeriesRef logic and clear the active ones
old_goto = """    const handleGoToRealTime = () => {
        if (!chartRef.current) return;
        setActiveTradeId(null);
        activeTradeRef.current = null;
        
        tradeSeriesRef.current.forEach(s => {
            try { chartRef.current?.removeSeries(s.tpSeries); } catch(e){}
            try { chartRef.current?.removeSeries(s.slSeries); } catch(e){}
        });
        tradeSeriesRef.current = [];
        
        try {
            if (seriesRef.current) seriesRef.current.priceScale().applyOptions({ autoScale: true });
        } catch(e) {}"""

new_goto = """    const handleGoToRealTime = () => {
        if (!chartRef.current) return;
        setActiveTradeId(null);
        activeTradeRef.current = null;
        
        tradeSeriesRef.current.forEach(s => {
            try { chartRef.current?.removeSeries(s.tpSeries); } catch(e){}
            try { chartRef.current?.removeSeries(s.slSeries); } catch(e){}
        });
        tradeSeriesRef.current = [];
        
        try {
            if (seriesRef.current) seriesRef.current.priceScale().applyOptions({ autoScale: true });
        } catch(e) {}"""

content = content.replace(old_goto, new_goto) # just confirming it is there

# 5. In handleTradeClick, draw the specific trade!
old_click = """        const padding = symbol === "DOGEUSDT" ? 2 * 3600 : 72 * 3600;
        const endTime = trade.exit_time || (candleDataRef.current.length > 0 ? candleDataRef.current[candleDataRef.current.length - 1].time : trade.time + 3600);
        chartRef.current.timeScale().setVisibleRange({
            from: (trade.time - padding) as any,
            to: (endTime + padding) as any
        });"""

new_click = """        const padding = symbol === "DOGEUSDT" ? 2 * 3600 : 72 * 3600;
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
        });"""

content = content.replace(old_click, new_click)

with open("components/ChartWidget.tsx", "w") as f:
    f.write(content)
print("Patched!")
