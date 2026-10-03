import re

with open("kline_cache.py", "r") as f:
    content = f.read()

# Replace CSV logic with DB logic
new_imports = """import os
import asyncio
import pandas as pd
import ccxt.async_support as ccxt
import time
from database import engine
from sqlalchemy import text"""

content = re.sub(r'import os\nimport asyncio\nimport pandas as pd\nimport ccxt\.async_support as ccxt\nimport time', new_imports, content)

old_logic = """    csv_file = f"data/{cache_key}.csv"
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
            last_time = int(df['time'].iloc[-1]) * 1000"""

new_logic = """    table_name = f"klines_{symbol.lower()}_{interval}"
    
    print(f"Initializing Persistent Cache for {cache_key}...")
    exchange = ccxt.binance({'enableRateLimit': True})
    
    try:
        # 1. Load from Database if exists
        with engine.connect() as conn:
            table_exists = conn.execute(text(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}';")).fetchone()
            
        if table_exists:
            print(f"Loading {cache_key} from SQLite Database...")
            df = pd.read_sql(f"SELECT * FROM {table_name} ORDER BY time ASC", con=engine)
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
            last_time = int(df['time'].iloc[-1]) * 1000"""

content = content.replace(old_logic, new_logic)


old_sync_logic = """                # Combine, drop dupes, save
                df = pd.concat([df, new_df]).drop_duplicates(subset=['time'], keep='last').sort_values('time')
                df.to_csv(csv_file, index=False)
                print(f"Synced {len(new_df)} new candles to CSV!")"""

new_sync_logic = """                # Append to DB directly
                new_df.to_sql(table_name, con=engine, if_exists='append', index=False)
                
                # Combine in memory
                df = pd.concat([df, new_df]).drop_duplicates(subset=['time'], keep='last').sort_values('time')
                print(f"Synced {len(new_df)} new candles to Database!")"""

content = content.replace(old_sync_logic, new_sync_logic)

with open("kline_cache.py", "w") as f:
    f.write(content)
