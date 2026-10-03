import sys

content = open("web_app/backend/main.py").read()

old_route = """@app.post("/api/test_order")
async def test_order():
    from engine.exchange import BinanceFutures
    exchange = BinanceFutures()
    try:
        symbol = 'DOGE/USDT'
        side = 'buy'
        amount = 150
        entry_price = 0.05000 
        sl_price = 0.04000
        tp_price = 0.50000
        
        await exchange.execute_full_trade(symbol, side, amount, entry_price, sl_price, tp_price)
        return {"status": "ok", "message": f"Đặt thành công cụm 3 lệnh: LIMIT (0.05), SL (0.04), TP (0.50)"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        await exchange.close()"""

new_route = """from pydantic import BaseModel
class TestOrderRequest(BaseModel):
    entry_price: float
    side: str

@app.post("/api/test_order")
async def test_order(req: TestOrderRequest):
    try:
        return await engine.execute_test_trade(req.entry_price, req.side)
    except Exception as e:
        return {"status": "error", "message": str(e)}"""

content = content.replace(old_route, new_route)

with open("web_app/backend/main.py", "w") as f:
    f.write(content)

