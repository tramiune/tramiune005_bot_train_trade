import os
import pandas as pd
from database import engine
from sqlalchemy import text

csv_file = "data/DOGEUSDT_3m.csv"
table_name = "klines_dogeusdt_3m"

if os.path.exists(csv_file):
    print("Found CSV! Importing to DB...")
    df = pd.read_csv(csv_file)
    df.to_sql(table_name, con=engine, if_exists='replace', index=False)
    with engine.connect() as conn:
        conn.execute(text(f"CREATE INDEX IF NOT EXISTS idx_{table_name}_time ON {table_name} (time);"))
        conn.commit()
    print("Import complete! You can delete the data folder now.")
else:
    print("No CSV found.")
