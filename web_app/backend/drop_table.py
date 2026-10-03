from database import engine
from sqlalchemy import text
with engine.connect() as conn:
    conn.execute(text("DROP TABLE IF EXISTS klines_dogeusdt_3m;"))
    conn.commit()
print("Table dropped!")
