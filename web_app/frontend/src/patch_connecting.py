import re

with open("components/ChartWidget.tsx", "r") as f:
    content = f.read()

old_else = """            } else {
                candleDataRef.current = formattedData;
                if (seriesRef.current) {
                    seriesRef.current.setData(candleDataRef.current);"""

new_else = """            } else {
                candleDataRef.current = formattedData;
                if (seriesRef.current) {
                    seriesRef.current.setData(candleDataRef.current);
                    setLastUpdate(new Date());"""

content = content.replace(old_else, new_else)

with open("components/ChartWidget.tsx", "w") as f:
    f.write(content)
print("Chart connecting patched!")
