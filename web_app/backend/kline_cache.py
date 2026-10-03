import os
import asyncio
import pandas as pd
import ccxt.async_support as ccxt
import time
from database import engine
from sqlalchemy import text

# In-memory cache for fast UI loading
KLINES_CACHE = {}

async def prefetch_klines():
    symbol = "DOGEUSDT"
    interval = "3m"
    cache_key = f"{symbol}_{interval}"
    table_name = f"klines_{symbol.lower()}_{interval}"
    
    print(f"Initializing Persistent Cache for {cache_key}...")
    exchange = ccxt.binance({'enableRateLimit': True, 'options': {'defaultType': 'future'}})
    
    try:
        # 1. Load from Database if exists
        with engine.connect() as conn:
            table_exists = conn.execute(text(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}';")).fetchone()
            
        if table_exists:
            print(f"Loading {cache_key} from SQLite Database...")
            df = pd.read_sql(f"SELECT * FROM {table_name} ORDER BY time DESC LIMIT 2000", con=engine)
            df = df.sort_values('time')
            last_time = int(df['time'].iloc[-1]) * 1000
            print(f"Loaded {len(df)} candles. Last time: {pd.to_datetime(last_time, unit='ms')}")
        else:
            print("No table found in DB. Fetching backwards 4 years... this will take a while.")
            from fetch_more import fetch_lots_of_klines
            doge_data = await fetch_lots_of_klines(exchange, "DOGE/USDT", interval, 710000)
            df = pd.DataFrame(doge_data, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
            df['time'] = (df['time'] / 1000).astype(int)
            # Create table and insert
            df.to_sql(table_name, con=engine, if_exists='replace', index=False)
            # Create index for faster querying
            with engine.connect() as conn:
                conn.execute(text(f"CREATE INDEX idx_{table_name}_time ON {table_name} (time);"))
                conn.commit()
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
                
                # Append to DB directly
                new_df.to_sql(table_name, con=engine, if_exists='append', index=False)
                
                # Combine in memory
                df = pd.concat([df, new_df]).drop_duplicates(subset=['time'], keep='last').sort_values('time')
                print(f"Synced {len(new_df)} new candles to Database!")

        # 3. Load to Memory
        KLINES_CACHE[cache_key] = df.tail(2000).to_dict(orient='records')
        print(f"Cache Ready! {len(KLINES_CACHE[cache_key])} total candles.")
    except Exception as e:
        print(f"Pre-fetch failed: {e}")
    finally:
        await exchange.close()
