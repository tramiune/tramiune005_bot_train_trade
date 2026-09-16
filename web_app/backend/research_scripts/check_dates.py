from datetime import datetime, timedelta, timezone
from server.main import _fetch_ohlcv_ccxt
since = datetime.now(timezone.utc) - timedelta(days=2920)
df = _fetch_ohlcv_ccxt("binance", "BTC/USDT", "1h", since=since, limit=100000)
print(f"Number of rows: {len(df)}")
print(f"Start date: {df['timestamp'].iloc[0]}")
print(f"End date: {df['timestamp'].iloc[-1]}")
