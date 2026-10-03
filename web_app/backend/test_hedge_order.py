import asyncio
from dotenv import load_dotenv
load_dotenv()
from engine.exchange import BinanceFutures

async def main():
    exchange = BinanceFutures()
    try:
        symbol = 'DOGE/USDT'
        side = 'buy'
        amount = 150
        price = 0.05000 
        
        print(f"Placing ENTRY Limit {side} for {amount} {symbol} at {price} (Hedge Mode LONG)")
        params = {'positionSide': 'LONG'}
        order = await exchange.exchange.create_order(symbol, 'limit', side, amount, price, params=params)
        print("SUCCESS! Order ID:", order['id'])
        
        # Now cancel it
        print("Canceling order...")
        await exchange.exchange.cancel_order(order['id'], symbol)
        print("Canceled.")
    except Exception as e:
        print(f"FAILED: {e}")
    finally:
        await exchange.close()

asyncio.run(main())
