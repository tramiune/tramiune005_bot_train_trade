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
    try:
        res = await ex.exchange.fapiPrivateGetPositionSideDual()
        print("Hedge mode:", res)
    except Exception as e:
        print("Hedge check error:", e)
        
    try:
        print(f"Testing SL: STOP_MARKET {close_side} {formatted_amount} stopPrice={formatted_sl}")
        sl_params = {'stopPrice': formatted_sl, 'reduceOnly': True}
        o = await ex.exchange.create_order(symbol, 'STOP_MARKET', close_side, formatted_amount, params=sl_params)
        print("SL SUCCESS! Order:", o['id'], o['status'])
    except Exception as e:
        print("SL FAILED:", e)
        
    try:
        print(f"Testing TP: TAKE_PROFIT_MARKET {close_side} {formatted_amount} stopPrice={formatted_tp}")
        tp_params = {'stopPrice': formatted_tp, 'reduceOnly': True}
        o = await ex.exchange.create_order(symbol, 'TAKE_PROFIT_MARKET', close_side, formatted_amount, params=tp_params)
        print("TP SUCCESS! Order:", o['id'], o['status'])
    except Exception as e:
        print("TP FAILED:", e)
        
    await ex.close()

asyncio.run(main())
