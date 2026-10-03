import asyncio
from dotenv import load_dotenv
load_dotenv()
from engine.exchange import BinanceFutures

async def main():
    exchange = BinanceFutures()
    try:
        symbol = 'DOGE/USDT'
        side = 'buy'
        amount = 150  # 150 DOGE (to ensure > 5 USDT notional)
        price = 0.05000 # Very far below current price
        
        print(f"Placing test LIMIT {side} order for {amount} {symbol} at {price}")
        order = await exchange.exchange.create_order(symbol, 'limit', side, amount, price)
        print("SUCCESS! Order ID:", order['id'])
    except Exception as e:
        print(f"FAILED: {e}")
    finally:
        await exchange.close()

asyncio.run(main())
