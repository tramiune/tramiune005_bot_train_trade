import re

with open("web_app/backend/main.py", "r") as f:
    content = f.read()

new_api = """@app.post("/api/test_order")
async def test_order():
    from engine.exchange import BinanceFutures
    exchange = BinanceFutures()
    try:
        symbol = 'DOGE/USDT'
        side = 'buy'
        amount = 150
        price = 0.05000 
        
        # We use execute_full_trade to test the entire Limit + SL + TP flow!
        # But wait, execute_full_trade places SL/TP based on the values.
        # If we use execute_full_trade, it will place Limit at 0.05, SL at 0.04, TP at 0.06.
        # Let's just place a raw Limit order to keep it simple and safe.
        
        await exchange.load_markets()
        
        # Check Hedge Mode
        is_hedge = False
        try:
            res = await exchange.exchange.fapiPrivateGetPositionSideDual()
            is_hedge = res.get('dualSidePosition', False)
        except Exception:
            pass
            
        params = {}
        if is_hedge:
            params['positionSide'] = 'LONG'
            
        order = await exchange.exchange.create_order(symbol, 'limit', side, amount, price, params=params)
        return {"status": "ok", "order_id": order['id'], "message": f"Đặt thành công lệnh LIMIT mua 150 DOGE ở giá $0.05. Mã lệnh: {order['id']}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        await exchange.close()

@app.get("/api/balance")"""

content = content.replace("@app.get(\"/api/balance\")", new_api)

with open("web_app/backend/main.py", "w") as f:
    f.write(content)
