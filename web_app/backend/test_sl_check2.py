import asyncio
from dotenv import load_dotenv
load_dotenv()
from engine.exchange import BinanceFutures

async def main():
    ex = BinanceFutures()
    symbol = "XRP/USDT"
    close_side = "sell"
    formatted_amount = 10.0
    formatted_sl = 1.4960
    formatted_tp = 1.7700
    
    await ex.load_markets()
    
    # Test SL with positionSide LONG
    try:
        print("Testing SL with positionSide='LONG':")
        sl_params = {'stopPrice': formatted_sl, 'positionSide': 'LONG'}
        o = await ex.exchange.create_order(symbol, 'STOP_MARKET', close_side, formatted_amount, params=sl_params)
        print("SL SUCCESS! Order:", o['id'], o['status'])
    except Exception as e:
        print("SL with positionSide='LONG' FAILED:", e)

    # Test TP with positionSide LONG
    try:
        print("Testing TP with positionSide='LONG':")
        tp_params = {'stopPrice': formatted_tp, 'positionSide': 'LONG'}
        o = await ex.exchange.create_order(symbol, 'TAKE_PROFIT_MARKET', close_side, formatted_amount, params=tp_params)
        print("TP SUCCESS! Order:", o['id'], o['status'])
    except Exception as e:
        print("TP with positionSide='LONG' FAILED:", e)
        
    await ex.close()

asyncio.run(main())
