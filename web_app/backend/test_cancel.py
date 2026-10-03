import asyncio
from dotenv import load_dotenv
load_dotenv()
from engine.exchange import BinanceFutures

async def main():
    exchange = BinanceFutures()
    try:
        res = await exchange.exchange.fapiPrivateDeleteAllOpenOrders({'symbol': 'DOGEUSDT'})
        print("SUCCESS!", res)
    except Exception as e:
        print(f"FAILED: {e}")
    finally:
        await exchange.close()

asyncio.run(main())
