import asyncio
import pandas as pd
import ccxt.async_support as ccxt
from fetch_more import fetch_lots_of_klines

# In-memory cache for fast UI loading
KLINES_CACHE = {}

async def prefetch_klines():
    print("Pre-fetching 4 years of DOGE 3m candles to memory for fast UI...")
    exchange = ccxt.binance({'enableRateLimit': True})
    
    try:
        # Fetch ~710000 candles (4 years 3m)
        doge_data = await fetch_lots_of_klines(exchange, "DOGE/USDT", '3m', 710000)
        
        # Format as list of dicts for instant JSON serialization
        formatted = []
        for d in doge_data:
            formatted.append({
                "time": int(d[0] / 1000),
                "open": float(d[1]),
                "high": float(d[2]),
                "low": float(d[3]),
                "close": float(d[4]),
                "volume": float(d[5])
            })
            
        KLINES_CACHE['DOGEUSDT_3m'] = formatted
        print(f"Pre-fetch complete! Cached {len(formatted)} candles.")
    except Exception as e:
        print(f"Pre-fetch failed: {e}")
    finally:
        await exchange.close()
