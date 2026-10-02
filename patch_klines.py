import re

with open("web_app/backend/main.py", "r") as f:
    content = f.read()

old_klines = """    cache_key = f"{symbol}_{interval}"
    if cache_key not in KLINES_CACHE:
        return {"status": "loading", "data": []}
        
    data = KLINES_CACHE[cache_key]"""

new_klines = """    cache_key = f"{symbol}_{interval}"
    
    if cache_key not in KLINES_CACHE:
        # Fallback to direct fetch if cache is still building
        import ccxt
        exchange = ccxt.binance()
        params = {}
        if endTime:
            params['endTime'] = endTime
        ohlcv = exchange.fetch_ohlcv(symbol.replace('USDT', '/USDT'), interval, limit=limit, params=params)
        formatted = [{"time": int(d[0] / 1000), "open": float(d[1]), "high": float(d[2]), "low": float(d[3]), "close": float(d[4]), "volume": float(d[5])} for d in ohlcv]
        return {"status": "success", "data": formatted}
        
    data = KLINES_CACHE[cache_key]"""

content = content.replace(old_klines, new_klines)

with open("web_app/backend/main.py", "w") as f:
    f.write(content)
