import re

with open("web_app/backend/main.py", "r") as f:
    content = f.read()

content = content.replace("await exchange.exchange.cancel_all_orders(symbol)", "await exchange.exchange.fapiPrivateDeleteAllOpenOrders({'symbol': symbol.replace('/', '')})")

with open("web_app/backend/main.py", "w") as f:
    f.write(content)

with open("web_app/backend/engine/trader.py", "r") as f:
    trader_content = f.read()

trader_content = trader_content.replace("await self.exchange.exchange.cancel_all_orders(trade.symbol)", "await self.exchange.exchange.fapiPrivateDeleteAllOpenOrders({'symbol': trade.symbol.replace('/', '')})")

with open("web_app/backend/engine/trader.py", "w") as f:
    f.write(trader_content)
