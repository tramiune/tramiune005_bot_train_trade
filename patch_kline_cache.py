import sys

content = open("web_app/backend/kline_cache.py").read()
content = content.replace("df = pd.read_sql(f\"SELECT * FROM {table_name} ORDER BY time ASC\", con=engine)", "df = pd.read_sql(f\"SELECT * FROM {table_name} ORDER BY time DESC LIMIT 2000\", con=engine)\n            df = df.sort_values('time')")
content = content.replace("KLINES_CACHE[cache_key] = df.to_dict(orient='records')", "KLINES_CACHE[cache_key] = df.tail(2000).to_dict(orient='records')")

with open("web_app/backend/kline_cache.py", "w") as f:
    f.write(content)
