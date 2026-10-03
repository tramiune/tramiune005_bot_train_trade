import re

with open("web_app/backend/kline_cache.py", "r") as f:
    content = f.read()

old_load = """        df = pd.read_sql_query(query, engine)
        
        # Convert to list of dicts"""
        
new_load = """        df = pd.read_sql_query(query, engine)
        df = df.drop_duplicates(subset=['time'], keep='last')
        
        # Convert to list of dicts"""
        
content = content.replace(old_load, new_load)

with open("web_app/backend/kline_cache.py", "w") as f:
    f.write(content)
print("kline_cache dupes patched!")
