import re

with open("web_app/backend/engine/exchange.py", "r") as f:
    content = f.read()

old_exchange = """def get_exchange():
    return ccxt.binance({
        'enableRateLimit': True,
    })"""

new_exchange = """def get_exchange():
    import os
    api_key = os.getenv("BINANCE_API_KEY", "")
    secret = os.getenv("BINANCE_SECRET", "")
    
    return ccxt.binance({
        'apiKey': api_key,
        'secret': secret,
        'enableRateLimit': True,
        'options': {
            'defaultType': 'future'  # Use Binance Futures
        }
    })"""

content = content.replace(old_exchange, new_exchange)

with open("web_app/backend/engine/exchange.py", "w") as f:
    f.write(content)
