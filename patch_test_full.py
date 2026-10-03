import re

with open("web_app/backend/main.py", "r") as f:
    content = f.read()

# Replace test_order to use execute_full_trade
old_test = """@app.post("/api/test_order")
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
        await exchange.close()"""

new_test = """@app.post("/api/test_order")
async def test_order():
    from engine.exchange import BinanceFutures
    exchange = BinanceFutures()
    try:
        symbol = 'DOGE/USDT'
        side = 'buy'
        amount = 150
        entry_price = 0.05000 
        sl_price = 0.04000
        tp_price = 0.06000
        
        await exchange.execute_full_trade(symbol, side, amount, entry_price, sl_price, tp_price)
        return {"status": "ok", "message": f"Đặt thành công cụm 3 lệnh: LIMIT (0.05), SL (0.04), TP (0.06)"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        await exchange.close()

@app.post("/api/cancel_orders")
async def cancel_orders():
    from engine.exchange import BinanceFutures
    exchange = BinanceFutures()
    try:
        symbol = 'DOGE/USDT'
        await exchange.exchange.cancel_all_orders(symbol)
        return {"status": "ok", "message": "Đã hủy toàn bộ lệnh treo trên Binance!"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        await exchange.close()"""

content = content.replace(old_test, new_test)

with open("web_app/backend/main.py", "w") as f:
    f.write(content)

