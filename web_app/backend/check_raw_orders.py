import asyncio
from dotenv import load_dotenv
load_dotenv()
from engine.exchange import BinanceFutures

async def main():
    ex = BinanceFutures()
    symbol = "XRP/USDT"
    await ex.load_markets()
    
    # Check open orders via fapiPrivateV2GetOpenOrders or raw API
    try:
        raw_open = await ex.exchange.fapiPrivateGetOpenOrders({'symbol': 'XRPUSDT'})
        print("fapiPrivateGetOpenOrders count:", len(raw_open))
        for r in raw_open:
            print("  raw:", r)
    except Exception as e:
        print("fapiPrivateGetOpenOrders err:", e)
        
    try:
        # Check conditional / algo endpoint
        # In Binance Futures API documentation:
        # GET /fapi/v1/openOrders returns all open orders including STOP_MARKET
        # But for Hedge mode, does it need symbol?
        all_orders = await ex.exchange.fapiPrivateGetAllOrders({'symbol': 'XRPUSDT', 'limit': 5})
        print("fapiPrivateGetAllOrders count:", len(all_orders))
        for o in all_orders:
            print("  order:", o.get('orderId'), o.get('clientOrderId'), o.get('type'), o.get('status'), o.get('stopPrice'))
    except Exception as e:
        print("fapiPrivateGetAllOrders err:", e)

    await ex.close()

asyncio.run(main())
