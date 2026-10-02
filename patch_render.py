import re

with open("web_app/frontend/src/components/ChartWidget.tsx", "r") as f:
    content = f.read()

content = content.replace(
    "const renderBacktest = (trades: any[]) => {",
    "const renderBacktest = (trades: any[], shouldPan: boolean = true) => {"
)

old_pan = """            // Use handleTradeClick to properly zoom and fetch historical candles if necessary
            const latest = trades[trades.length - 1];
            setTimeout(() => {
                handleTradeClick(latest);
            }, 500);"""

new_pan = """            if (shouldPan) {
                const latest = trades[trades.length - 1];
                setTimeout(() => {
                    handleTradeClick(latest);
                }, 50);
            }"""

content = content.replace(old_pan, new_pan)

content = content.replace("renderBacktest(frontendCache[symbol])", "renderBacktest(frontendCache[symbol], false)")

with open("web_app/frontend/src/components/ChartWidget.tsx", "w") as f:
    f.write(content)
