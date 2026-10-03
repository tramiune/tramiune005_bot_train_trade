import re

with open("web_app/backend/main.py", "r") as f:
    content = f.read()

old_cancel = "await exchange.exchange.fapiPrivateDeleteAllOpenOrders({'symbol': symbol.replace('/', '')})"
new_cancel = """await exchange.exchange.fapiPrivateDeleteAllOpenOrders({'symbol': symbol.replace('/', '')})
        try:
            await exchange.exchange.fapiPrivateDeleteAlgoOpenOrders({'symbol': symbol.replace('/', '')})
        except Exception:
            pass"""

content = content.replace(old_cancel, new_cancel)

with open("web_app/backend/main.py", "w") as f:
    f.write(content)

with open("web_app/backend/engine/trader.py", "r") as f:
    trader_content = f.read()

trader_content = trader_content.replace(old_cancel, new_cancel)

with open("web_app/backend/engine/trader.py", "w") as f:
    f.write(trader_content)
