import asyncio
import ccxt.async_support as ccxt
import pandas as pd
from models import Trade
from database import SessionLocal

async def main():
    db = SessionLocal()
    open_trades = db.query(Trade).filter(Trade.status == "OPEN").all()
    if not open_trades:
        print("No open trades to fix.")
        return
        
    exchange = ccxt.binance()
    for trade in open_trades:
        # Fetch candles since trade entry time
        since = int(pd.to_datetime(trade.entry_time).timestamp() * 1000)
        ohlcv = await exchange.fetch_ohlcv(trade.symbol, '1m', since=since, limit=1500)
        if not ohlcv:
            continue
            
        closed = False
        for candle in ohlcv:
            c_time, c_open, c_high, c_low, c_close, c_vol = candle
            if trade.side == 'LONG':
                if c_low <= trade.stop_loss:
                    trade.status = "CLOSED"
                    trade.exit_price = trade.stop_loss
                    trade.pnl = -1
                    trade.exit_time = pd.to_datetime(c_time, unit='ms').to_pydatetime()
                    closed = True; break
                elif c_high >= trade.take_profit:
                    trade.status = "CLOSED"
                    trade.exit_price = trade.take_profit
                    trade.pnl = 1
                    trade.exit_time = pd.to_datetime(c_time, unit='ms').to_pydatetime()
                    closed = True; break
            else:
                if c_high >= trade.stop_loss:
                    trade.status = "CLOSED"
                    trade.exit_price = trade.stop_loss
                    trade.pnl = -1
                    trade.exit_time = pd.to_datetime(c_time, unit='ms').to_pydatetime()
                    closed = True; break
                elif c_low <= trade.take_profit:
                    trade.status = "CLOSED"
                    trade.exit_price = trade.take_profit
                    trade.pnl = 1
                    trade.exit_time = pd.to_datetime(c_time, unit='ms').to_pydatetime()
                    closed = True; break
                    
        if closed:
            print(f"Fixed trade {trade.id}: hit {'TP' if trade.pnl > 0 else 'SL'} at {trade.exit_time}")
        else:
            print(f"Trade {trade.id} is STILL genuinely OPEN!")
            
    db.commit()
    db.close()
    await exchange.close()

asyncio.run(main())
