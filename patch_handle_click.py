import re

with open("web_app/frontend/src/components/ChartWidget.tsx", "r") as f:
    content = f.read()

# Add try-catch around handleTradeClick priceScale logic
old_logic = """        if (seriesRef.current) {
            seriesRef.current.priceScale().applyOptions({ autoScale: false });
            setTimeout(() => {
                if (seriesRef.current) seriesRef.current.priceScale().applyOptions({ autoScale: true });
            }, 100);
        }"""

new_logic = """        try {
            if (seriesRef.current) {
                // Check if it has data to prevent priceScale crash
                const data = seriesRef.current.data();
                if (data && data.length > 0) {
                    seriesRef.current.priceScale().applyOptions({ autoScale: false });
                    setTimeout(() => {
                        try {
                            if (seriesRef.current) seriesRef.current.priceScale().applyOptions({ autoScale: true });
                        } catch(e) {}
                    }, 100);
                }
            }
        } catch (e) {
            console.warn("Could not apply price scale", e);
        }"""

content = content.replace(old_logic, new_logic)

with open("web_app/frontend/src/components/ChartWidget.tsx", "w") as f:
    f.write(content)
