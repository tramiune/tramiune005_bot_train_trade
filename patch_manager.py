import re

with open("web_app/backend/engine/trader.py", "r") as f:
    content = f.read()

old_logic = """            symbols = list(set([t.symbol for t in open_trades]))
            prices = {}
            for sym in symbols:
                ohlcv = await self.exchange.fetch_ohlcv(sym, '1m', limit=10)
                if ohlcv:
                    prices[sym] = ohlcv
                    
            for trade in open_trades:
                if trade.symbol not in prices:
                    continue
                
                # Check recent candles
                for candle in prices[trade.symbol]:"""

new_logic = """            for trade in open_trades:
                # Fetch 3m candles since entry to ensure we don't miss a spike while offline
                import pandas as pd
                since = int(pd.to_datetime(trade.entry_time).timestamp() * 1000)
                # Fetch up to 1500 3m candles (approx 3 days)
                ohlcv = await self.exchange.fetch_ohlcv(trade.symbol, '3m', since=since, limit=1500)
                if not ohlcv:
                    continue
                
                # Check candles
                for candle in ohlcv:"""

content = content.replace(old_logic, new_logic)

with open("web_app/backend/engine/trader.py", "w") as f:
    f.write(content)
