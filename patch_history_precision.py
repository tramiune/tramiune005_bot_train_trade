import re

with open("web_app/frontend/src/components/TradeHistory.tsx", "r") as f:
    content = f.read()

content = content.replace("toFixed(4)", "toFixed(5)")
content = content.replace("'0.0000'", "'0.00000'")

with open("web_app/frontend/src/components/TradeHistory.tsx", "w") as f:
    f.write(content)
