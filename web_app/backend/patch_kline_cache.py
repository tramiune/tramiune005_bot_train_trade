import re

with open("web_app/backend/kline_cache.py", "r") as f:
    content = f.read()

old_ex = "exchange = ccxt.binance()"
new_ex = "exchange = ccxt.binance({'options': {'defaultType': 'future'}})"
content = content.replace(old_ex, new_ex)

with open("web_app/backend/kline_cache.py", "w") as f:
    f.write(content)
print("kline_cache patched!")
