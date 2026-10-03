import re

with open("components/ChartWidget.tsx", "r") as f:
    content = f.read()

# Use regex to find and remove the entire backtestTrades conditional block
pattern = r'\{!isBacktestLoading && backtestTrades\.length > 0 && \(\s*<div className="bg-gray-800.*?</div>\s*\)\}'
content = re.sub(pattern, '', content, flags=re.DOTALL)

with open("components/ChartWidget.tsx", "w") as f:
    f.write(content)
