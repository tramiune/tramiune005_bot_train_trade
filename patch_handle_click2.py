import re

with open("web_app/frontend/src/components/ChartWidget.tsx", "r") as f:
    content = f.read()

content = content.replace("const data = seriesRef.current.data();", "const data = candleDataRef.current;")

with open("web_app/frontend/src/components/ChartWidget.tsx", "w") as f:
    f.write(content)
