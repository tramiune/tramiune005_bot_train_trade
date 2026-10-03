import re

with open("web_app/frontend/src/components/ChartWidget.tsx", "r") as f:
    content = f.read()

old_ws = """            if (candleDataRef.current.length > 0) {
                const lastIdx = candleDataRef.current.length - 1;
                if (candleDataRef.current[lastIdx].time === newTick.time) {
                    candleDataRef.current[lastIdx] = newTick;
                } else if (newTick.time > candleDataRef.current[lastIdx].time) {
                    candleDataRef.current.push(newTick);
                }
            }
        };"""

new_ws = """            if (candleDataRef.current.length > 0) {
                const lastIdx = candleDataRef.current.length - 1;
                if (candleDataRef.current[lastIdx].time === newTick.time) {
                    candleDataRef.current[lastIdx] = newTick;
                } else if (newTick.time > candleDataRef.current[lastIdx].time) {
                    candleDataRef.current.push(newTick);
                }
                
                // Update indicators dynamically
                if (symbol === 'DOGEUSDT') {
                    const bbData = calculateBB(candleDataRef.current, 20, 2.0);
                    const kcData = calculateKC(candleDataRef.current, 20, 2.0);
                    
                    if (bbData.upper.length > 0 && bbUpperSeriesRef.current) bbUpperSeriesRef.current.update(bbData.upper[bbData.upper.length - 1]);
                    if (bbData.lower.length > 0 && bbLowerSeriesRef.current) bbLowerSeriesRef.current.update(bbData.lower[bbData.lower.length - 1]);
                    if (bbData.mid.length > 0 && midSeriesRef.current) midSeriesRef.current.update(bbData.mid[bbData.mid.length - 1]);
                    if (kcData.upper.length > 0 && kcUpperSeriesRef.current) kcUpperSeriesRef.current.update(kcData.upper[kcData.upper.length - 1]);
                    if (kcData.lower.length > 0 && kcLowerSeriesRef.current) kcLowerSeriesRef.current.update(kcData.lower[kcData.lower.length - 1]);
                } else {
                    const ema20 = calculateEMA(candleDataRef.current, 20);
                    const ema200 = calculateEMA(candleDataRef.current, 200);
                    if (ema20.length > 0 && ema20SeriesRef.current) ema20SeriesRef.current.update(ema20[ema20.length - 1]);
                    if (ema200.length > 0 && ema200SeriesRef.current) ema200SeriesRef.current.update(ema200[ema200.length - 1]);
                }
            }
        };"""

content = content.replace(old_ws, new_ws)

with open("web_app/frontend/src/components/ChartWidget.tsx", "w") as f:
    f.write(content)
