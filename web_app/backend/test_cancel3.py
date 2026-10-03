import asyncio
from dotenv import load_dotenv
load_dotenv()
from engine.exchange import BinanceFutures

async def main():
    exchange = BinanceFutures()
    try:
        # Place SL
        sl_params = {'stopPrice': 0.03, 'positionSide': 'LONG'}
        order = await exchange.exchange.create_order('DOGE/USDT', 'STOP_MARKET', 'sell', 150, params=sl_params)
        print("Placed SL:", order['id'])
        
        # Cancel Algo orders
        res = await exchange.exchange.fapiPrivateDeleteAlgoOpenOrders({'symbol': 'DOGEUSDT'})
        print("Cancel response:", res)
        
    except Exception as e:
        print(f"FAILED: {e}")
    finally:
        await exchange.close()

asyncio.run(main())
