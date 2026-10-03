import asyncio
import ccxt.async_support as ccxt
import pandas as pd
import time

async def fetch_lots_of_klines(exchange, symbol, timeframe, limit=5000):
    all_ohlcv = []
    since = None
    end_time = None
    
    start_time = time.time()
    
    while len(all_ohlcv) < limit:
        params = {}
        if end_time:
            params['endTime'] = end_time
            
        fetch_limit = min(1500, limit - len(all_ohlcv))
        ohlcv = await exchange.fetch_ohlcv(symbol, timeframe, limit=fetch_limit, params=params)
        
        if not ohlcv:
            break
            
        all_ohlcv = ohlcv + all_ohlcv
        end_time = ohlcv[0][0] - 1
        
        if len(all_ohlcv) % 15000 == 0:
            print(f"Fetched {len(all_ohlcv)}/{limit} candles so far... ({(time.time() - start_time):.1f}s)")
        
    return all_ohlcv
