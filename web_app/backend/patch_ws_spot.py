import re

with open("web_app/backend/ws_engine.py", "r") as f:
    content = f.read()

content = content.replace("wss://fstream.binance.com/ws/{symbol}@kline_{interval}", "wss://stream.binance.com:9443/ws/{symbol}@kline_{interval}")

with open("web_app/backend/ws_engine.py", "w") as f:
    f.write(content)
print("Reverted to Spot WS!")
