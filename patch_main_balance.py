import re

with open("web_app/backend/main.py", "r") as f:
    content = f.read()

new_api = """@app.get("/api/balance")
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
        await exchange.close()

@app.get("/api/telegram/status")"""

content = content.replace("@app.get(\"/api/telegram/status\")", new_api)

with open("web_app/backend/main.py", "w") as f:
    f.write(content)
