import re

with open("web_app/frontend/src/components/ChartWidget.tsx", "r") as f:
    content = f.read()

old_end = "const endTime = trade.exit_time || trade.time;"
new_end = "const endTime = trade.exit_time || (candleDataRef.current.length > 0 ? candleDataRef.current[candleDataRef.current.length - 1].time : trade.time + 3600);"

content = content.replace(old_end, new_end)

with open("web_app/frontend/src/components/ChartWidget.tsx", "w") as f:
    f.write(content)
