import asyncio
from dotenv import load_dotenv
load_dotenv()
from engine.exchange import BinanceFutures

async def main():
    exchange = BinanceFutures()
    try:
        symbol = 'DOGE/USDT'
        close_side = 'sell'
        formatted_amount = 150
        formatted_sl = 0.04
        sl_params = {'stopPrice': formatted_sl, 'positionSide': 'LONG'}
        order = await exchange.exchange.create_order(symbol, 'STOP_MARKET', close_side, formatted_amount, params=sl_params)
        print("SL ORDER CREATED:", order['id'])
    except Exception as e:
        print(f"FAILED TO CREATE SL: {e}")
    finally:
        await exchange.close()

asyncio.run(main())
