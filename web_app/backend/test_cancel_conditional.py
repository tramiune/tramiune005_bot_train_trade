import asyncio
from dotenv import load_dotenv
load_dotenv()
from engine.exchange import BinanceFutures

async def main():
    exchange = BinanceFutures()
    try:
        symbol = 'DOGE/USDT'
        raw_symbol = 'DOGEUSDT'
        
        # 1. Place a STOP_MARKET order
        sl_params = {'stopPrice': 0.04, 'positionSide': 'LONG'}
        order = await exchange.exchange.create_order(symbol, 'STOP_MARKET', 'sell', 150, params=sl_params)
        print("Placed SL:", order['id'])
        
        # 2. Check open orders
        orders = await exchange.exchange.fetch_open_orders(symbol)
        print(f"Open orders before cancel: {len(orders)}")
        
        # 3. Call fapiPrivateDeleteAllOpenOrders
        res = await exchange.exchange.fapiPrivateDeleteAllOpenOrders({'symbol': raw_symbol})
        print("Cancel response:", res)
        
        # 4. Check open orders again
        orders_after = await exchange.exchange.fetch_open_orders(symbol)
        print(f"Open orders after cancel: {len(orders_after)}")
        
    except Exception as e:
        print(f"FAILED: {e}")
    finally:
        await exchange.close()

asyncio.run(main())
