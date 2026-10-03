import re

with open("components/ChartWidget.tsx", "r") as f:
    content = f.read()

old_goto = """    const handleGoToRealTime = () => {
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
    };"""

new_goto = """    const handleGoToRealTime = () => {
        if (!chartRef.current) return;
        chartRef.current.timeScale().scrollToRealTime();
        if (seriesRef.current) {
            seriesRef.current.priceScale().applyOptions({ autoScale: true });
        }
    };"""

content = content.replace(old_goto, new_goto)

with open("components/ChartWidget.tsx", "w") as f:
    f.write(content)
print("Patched!")
