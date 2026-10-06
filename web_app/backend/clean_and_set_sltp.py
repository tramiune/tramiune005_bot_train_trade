import asyncio
from dotenv import load_dotenv
load_dotenv()
from engine.exchange import BinanceFutures

async def main():
    ex = BinanceFutures()
    symbol = "XRP/USDT"
    symbol_raw = "XRPUSDT"
    await ex.load_markets()
    
    # 1. Clean existing orders
    try:
        await ex.exchange.fapiPrivateDeleteAllOpenOrders({'symbol': symbol_raw})
        await ex.exchange.fapiPrivateDeleteAlgoOpenOrders({'symbol': symbol_raw})
        print("Cleaned all existing orders.")
    except Exception as e:
        print("Clean err:", e)
        
    # 2. Place 1 clean SL and 1 clean TP
    sl_params = {'stopPrice': 1.4950, 'positionSide': 'LONG'}
    tp_params = {'stopPrice': 1.7740, 'positionSide': 'LONG'}
    
    sl_order = await ex.exchange.create_order(symbol, 'STOP_MARKET', 'sell', 10.0, params=sl_params)
    print("SL order created:", sl_order['id'], "at 1.4950")
    
    tp_order = await ex.exchange.create_order(symbol, 'TAKE_PROFIT_MARKET', 'sell', 10.0, params=tp_params)
    print("TP order created:", tp_order['id'], "at 1.7740")
    
    await ex.close()

asyncio.run(main())
