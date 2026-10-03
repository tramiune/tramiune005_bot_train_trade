import re

# 1. ws_engine.py
with open("web_app/backend/ws_engine.py", "r") as f:
    ws_content = f.read()

ws_content = ws_content.replace('wss://stream.binance.com:9443/ws/', 'wss://fstream.binance.com/ws/')

with open("web_app/backend/ws_engine.py", "w") as f:
    f.write(ws_content)

# 2. kline_cache.py
with open("web_app/backend/kline_cache.py", "r") as f:
    cache_content = f.read()

cache_content = cache_content.replace("ccxt.binance({'enableRateLimit': True})", "ccxt.binance({'enableRateLimit': True, 'options': {'defaultType': 'future'}})")

with open("web_app/backend/kline_cache.py", "w") as f:
    f.write(cache_content)

# 3. main.py
with open("web_app/backend/main.py", "r") as f:
    main_content = f.read()

main_content = main_content.replace("exchange = ccxt.binance()", "exchange = ccxt.binance({'options': {'defaultType': 'future'}})")

with open("web_app/backend/main.py", "w") as f:
    f.write(main_content)
