import re

with open("web_app/frontend/src/components/ChartWidget.tsx", "r") as f:
    content = f.read()

# Find the websocket block
ws_block = re.search(r'const wsUrl =.*?};\n\n', content, re.DOTALL)
if ws_block:
    content = content.replace(ws_block.group(0), "")

# We need to add setInterval to fetchKlines
old_fetch = """        fetchKlines().then(() => {
            fetchBacktest();
        });

        const onVisibleLogicalRangeChanged ="""

new_fetch = """        fetchKlines().then(() => {
            fetchBacktest();
        });
        
        // Poll backend for updates (candle close)
        const intervalId = setInterval(() => {
            fetchKlines();
        }, 5000);

        const onVisibleLogicalRangeChanged ="""

content = content.replace(old_fetch, new_fetch)

# Clear interval on unmount
old_unmount = """        return () => {
            chart.remove();
        };"""

new_unmount = """        return () => {
            clearInterval(intervalId);
            chart.remove();
        };"""

content = content.replace(old_unmount, new_unmount)

with open("web_app/frontend/src/components/ChartWidget.tsx", "w") as f:
    f.write(content)
