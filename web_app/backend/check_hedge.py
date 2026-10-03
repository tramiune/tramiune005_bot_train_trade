import asyncio
from dotenv import load_dotenv
load_dotenv()
from engine.exchange import BinanceFutures

async def main():
    exchange = BinanceFutures()
    try:
        # Fetch account info or position mode
        res = await exchange.exchange.fapiPrivateGetPositionSideDual()
        print("Position Mode Response:", res)
    except Exception as e:
        print(f"FAILED: {e}")
    finally:
        await exchange.close()

asyncio.run(main())
