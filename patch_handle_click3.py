import re

with open("web_app/frontend/src/components/ChartWidget.tsx", "r") as f:
    content = f.read()

old_logic = """        if (seriesRef.current) {
            seriesRef.current.priceScale().applyOptions({ autoScale: false });
            setTimeout(() => {
                if (seriesRef.current) seriesRef.current.priceScale().applyOptions({ autoScale: true });
            }, 50);
        }"""

new_logic = """        try {
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
        }"""

content = content.replace(old_logic, new_logic)

with open("web_app/frontend/src/components/ChartWidget.tsx", "w") as f:
    f.write(content)
