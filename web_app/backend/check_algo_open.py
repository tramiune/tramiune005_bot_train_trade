import asyncio
from dotenv import load_dotenv
load_dotenv()
from engine.exchange import BinanceFutures

async def main():
    ex = BinanceFutures()
    res = await ex.exchange.fapiPrivateGetOpenAlgoOrders({'symbol': 'XRPUSDT'})
    print("Open Algo Orders count:", len(res))
    for o in res:
        print("  Algo:", o.get('algoId'), o.get('orderType'), o.get('triggerPrice'), o.get('positionSide'))
    await ex.close()

asyncio.run(main())
