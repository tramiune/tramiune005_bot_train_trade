import re

with open("web_app/frontend/src/components/ChartWidget.tsx", "r") as f:
    content = f.read()

# Filter markers to only show those that fit inside candleDataRef.current bounds
old_marker = """            const markers = trades.map((t: any) => ({
                time: t.time,"""

new_marker = """            const firstCandleTime = candleDataRef.current.length > 0 ? candleDataRef.current[0].time : 0;
            const validTrades = trades.filter(t => t.time >= firstCandleTime);
            const markers = validTrades.map((t: any) => ({
                time: t.time,"""

content = content.replace(old_marker, new_marker)

# Make fetchKlines re-apply markers when older data is loaded
old_fetch = """                    const kcData = calculateKC(candleDataRef.current, 20, 1.5);
                    if (bbUpperSeriesRef.current) bbUpperSeriesRef.current.setData(bbData.upper);
                    if (bbLowerSeriesRef.current) bbLowerSeriesRef.current.setData(bbData.lower);
                    if (kcUpperSeriesRef.current) kcUpperSeriesRef.current.setData(kcData.upper);
                    if (kcLowerSeriesRef.current) kcLowerSeriesRef.current.setData(kcData.lower);
                    if (midSeriesRef.current) midSeriesRef.current.setData(bbData.mid);
                    reapplyMarkersAndLines();
                }
            } else {"""

new_fetch = """                    const kcData = calculateKC(candleDataRef.current, 20, 1.5);
                    if (bbUpperSeriesRef.current) bbUpperSeriesRef.current.setData(bbData.upper);
                    if (bbLowerSeriesRef.current) bbLowerSeriesRef.current.setData(bbData.lower);
                    if (kcUpperSeriesRef.current) kcUpperSeriesRef.current.setData(kcData.upper);
                    if (kcLowerSeriesRef.current) kcLowerSeriesRef.current.setData(kcData.lower);
                    if (midSeriesRef.current) midSeriesRef.current.setData(bbData.mid);
                    if (frontendCache[symbol]) renderBacktest(frontendCache[symbol]);
                    reapplyMarkersAndLines();
                }
            } else {"""

content = content.replace(old_fetch, new_fetch)

# Also update the catch block fetchKlines
old_fetch2 = """                    const kcData = calculateKC(uniqueData, 20, 1.5);
                    if (bbUpperSeriesRef.current) bbUpperSeriesRef.current.setData(bbData.upper);
                    if (bbLowerSeriesRef.current) bbLowerSeriesRef.current.setData(bbData.lower);
                    if (kcUpperSeriesRef.current) kcUpperSeriesRef.current.setData(kcData.upper);
                    if (kcLowerSeriesRef.current) kcLowerSeriesRef.current.setData(kcData.lower);
                    if (midSeriesRef.current) midSeriesRef.current.setData(bbData.mid);
                    reapplyMarkersAndLines();
                }"""

new_fetch2 = """                    const kcData = calculateKC(uniqueData, 20, 1.5);
                    if (bbUpperSeriesRef.current) bbUpperSeriesRef.current.setData(bbData.upper);
                    if (bbLowerSeriesRef.current) bbLowerSeriesRef.current.setData(bbData.lower);
                    if (kcUpperSeriesRef.current) kcUpperSeriesRef.current.setData(kcData.upper);
                    if (kcLowerSeriesRef.current) kcLowerSeriesRef.current.setData(kcData.lower);
                    if (midSeriesRef.current) midSeriesRef.current.setData(bbData.mid);
                    if (frontendCache[symbol]) renderBacktest(frontendCache[symbol]);
                    reapplyMarkersAndLines();
                }"""
                
content = content.replace(old_fetch2, new_fetch2)

with open("web_app/frontend/src/components/ChartWidget.tsx", "w") as f:
    f.write(content)
