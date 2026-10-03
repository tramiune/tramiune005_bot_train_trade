import re

with open("web_app/backend/main.py", "r") as f:
    content = f.read()

broken_api = """@app.get("/api/balance")
async def get_balance():
    from engine.exchange import get_exchange
    exchange = get_exchange()
    try:
        if not exchange.apiKey or not exchange.secret:
            return {"balance": 0.0, "status": "keys_missing"}
        
        balance = await exchange.fetch_balance()
        # USDT available balance in futures wallet
        usdt_free = balance.get('USDT', {}).get('free', 0.0)
        return {"balance": usdt_free, "status": "ok"}
    except Exception as e:
        return {"balance": 0.0, "status": "error", "message": str(e)}
    finally:
        await exchange.close()"""

fixed_api = """@app.get("/api/balance")
async def get_balance():
    from engine.exchange import BinanceFutures
    import os
    
    # Check if keys are empty strings
    api_key = os.getenv("BINANCE_API_KEY", "")
    secret = os.getenv("BINANCE_SECRET", "")
    if not api_key or not secret:
        return {"balance": 0.0, "status": "keys_missing"}
        
    engine_exchange = BinanceFutures()
    try:
        if not engine_exchange.exchange.apiKey or not engine_exchange.exchange.secret:
            return {"balance": 0.0, "status": "keys_missing"}
        
        balance = await engine_exchange.exchange.fetch_balance()
        # USDT available balance in futures wallet
        usdt_free = balance.get('USDT', {}).get('free', 0.0)
        return {"balance": usdt_free, "status": "ok"}
    except Exception as e:
        return {"balance": 0.0, "status": "error", "message": str(e)}
    finally:
        await engine_exchange.close()"""

content = content.replace(broken_api, fixed_api)

with open("web_app/backend/main.py", "w") as f:
    f.write(content)
