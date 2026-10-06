import asyncio
from dotenv import load_dotenv
load_dotenv()
from engine.exchange import BinanceFutures

async def main():
    ex = BinanceFutures()
    symbol = "XRP/USDT"
    await ex.load_markets()
    
    # Check order history
    try:
        orders = await ex.exchange.fetch_orders(symbol, limit=10)
        print(f"Recent orders count: {len(orders)}")
        for o in orders:
            print(f"Order {o['id']}: type={o.get('type')}, side={o.get('side')}, price={o.get('price')}, stopPrice={o.get('stopPrice')}, status={o.get('status')}")
    except Exception as e:
        print("fetch_orders err:", e)
        
    await ex.close()

asyncio.run(main())
