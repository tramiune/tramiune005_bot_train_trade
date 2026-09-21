import asyncio
import ccxt.async_support as ccxt
import pandas as pd

async def fetch_lots_of_klines(exchange, symbol, timeframe, limit=5000):
    all_ohlcv = []
    since = None
    # We want to go backwards, so we use endTime, but ccxt fetch_ohlcv doesn't natively support endTime well across all exchanges.
    # Binance supports it via params={'endTime': xxx}
    end_time = None
    
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
        
    return all_ohlcv
