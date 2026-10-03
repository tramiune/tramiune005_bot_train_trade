import re

with open("components/ChartWidget.tsx", "r") as f:
    content = f.read()

# Replace fetchKlines call
old_fetch = """        fetchKlines().then(() => {
            fetchBacktest();
        });"""

new_fetch = """        fetchKlines().then(() => {
            fetchBacktest();
        });
        
        // Poll backend for updates (candle close & new trades) every 5s
        const intervalId = setInterval(() => {
            fetchKlines().then(() => {
                fetchBacktest();
            });
        }, 5000);"""

content = content.replace(old_fetch, new_fetch)

# Replace cleanup
old_cleanup = """        return () => {
            
            chart.timeScale().unsubscribeVisibleLogicalRangeChange(onVisibleLogicalRangeChanged);
            
            chart.remove();
        };"""

new_cleanup = """        return () => {
            clearInterval(intervalId);
            chart.timeScale().unsubscribeVisibleLogicalRangeChange(onVisibleLogicalRangeChanged);
            chart.remove();
        };"""

content = content.replace(old_cleanup, new_cleanup)

with open("components/ChartWidget.tsx", "w") as f:
    f.write(content)
print("Polling patched!")
