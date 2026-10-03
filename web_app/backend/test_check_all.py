import asyncio
from dotenv import load_dotenv
load_dotenv()
from engine.exchange import BinanceFutures

async def main():
    exchange = BinanceFutures()
    try:
        raw_symbol = 'DOGEUSDT'
        
        orders = await exchange.exchange.fapiPrivateGetOpenOrders({'symbol': raw_symbol})
        print(f"Total RAW open orders on Binance: {len(orders)}")
        for o in orders:
            print(o['type'], o['origType'], o['status'])
            
    except Exception as e:
        print(f"FAILED: {e}")
    finally:
        await exchange.close()

asyncio.run(main())
