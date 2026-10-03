import os
import asyncio
import pandas as pd
import ccxt.async_support as ccxt
import time

# In-memory cache for fast UI loading
KLINES_CACHE = {}

async def prefetch_klines():
    symbol = "DOGEUSDT"
    interval = "3m"
    cache_key = f"{symbol}_{interval}"
    csv_file = f"data/{cache_key}.csv"
    os.makedirs("data", exist_ok=True)
    
    print(f"Initializing Persistent Cache for {cache_key}...")
    exchange = ccxt.binance({'enableRateLimit': True})
    
    try:
        # 1. Load from CSV if exists
        if os.path.exists(csv_file):
            print(f"Loading from local CSV {csv_file}...")
            df = pd.read_csv(csv_file)
            last_time = int(df['time'].iloc[-1]) * 1000
            print(f"Loaded {len(df)} candles. Last time: {pd.to_datetime(last_time, unit='ms')}")
        else:
            print("No local CSV. Fetching backwards 4 years... this will take a while.")
            from fetch_more import fetch_lots_of_klines
            # Fetch less during test if needed, but the user wants it to be robust
            doge_data = await fetch_lots_of_klines(exchange, "DOGE/USDT", interval, 710000)
            df = pd.DataFrame(doge_data, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
            df['time'] = (df['time'] / 1000).astype(int)
            df.to_csv(csv_file, index=False)
            last_time = int(df['time'].iloc[-1]) * 1000

        # 2. Sync forward to Real-Time
        now = int(time.time() * 1000)
        # Check if we are lagging by more than 1 interval
        interval_ms = 3 * 60 * 1000
        if now - last_time >= interval_ms:
            print(f"Syncing missed candles from {pd.to_datetime(last_time, unit='ms')} to Now...")
            new_candles = []
            since = last_time + 1 # Start right after the last candle
            while since < now:
                ohlcv = await exchange.fetch_ohlcv("DOGE/USDT", interval, since=since, limit=1000)
                if not ohlcv or len(ohlcv) == 0:
                    break
                new_candles.extend(ohlcv)
                since = ohlcv[-1][0] + 1
                await asyncio.sleep(0.05) # Rate limit
                
            if new_candles:
                new_df = pd.DataFrame(new_candles, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
                new_df['time'] = (new_df['time'] / 1000).astype(int)
                
                # Combine, drop dupes, save
                df = pd.concat([df, new_df]).drop_duplicates(subset=['time'], keep='last').sort_values('time')
                df.to_csv(csv_file, index=False)
                print(f"Synced {len(new_df)} new candles to CSV!")

        # 3. Load to Memory
        KLINES_CACHE[cache_key] = df.to_dict(orient='records')
        print(f"Cache Ready! {len(KLINES_CACHE[cache_key])} total candles.")
    except Exception as e:
        print(f"Pre-fetch failed: {e}")
    finally:
        await exchange.close()
