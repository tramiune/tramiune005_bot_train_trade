import asyncio
import pandas as pd
from database import engine, SessionLocal
from models import Trade
from fetch_more import fetch_lots_of_klines
from engine.backtester import backtest_doge_rr25, backtest_sol_god_mode
import ccxt.async_support as ccxt

async def main():
    exchange = ccxt.binance({'enableRateLimit': True})
    db = SessionLocal()
    
    print("Fetching DOGE data...")
    doge_data = await fetch_lots_of_klines(exchange, "DOGE/USDT", '1h', 35000)
    df_doge = pd.DataFrame(doge_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    doge_trades = backtest_doge_rr25(df_doge)
    
    print("Fetching SOL data...")
    sol_data = await fetch_lots_of_klines(exchange, "SOL/USDT", '1h', 35000)
    print("Fetching BTC data...")
    btc_data = await fetch_lots_of_klines(exchange, "BTC/USDT", '1h', 35000)
    
    df_sol = pd.DataFrame(sol_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df_btc = pd.DataFrame(btc_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    sol_trades = backtest_sol_god_mode(df_sol, df_btc)
    
    await exchange.close()
    
    print(f"Found {len(doge_trades)} DOGE trades and {len(sol_trades)} SOL trades.")
    
    from datetime import datetime
    
    # Check if we already have trades to avoid duplicates
    existing = db.query(Trade).count()
    if existing > 0:
        print("Clearing old trades...")
        db.query(Trade).delete()
        db.commit()

    print("Inserting to DB...")
    for t in doge_trades:
        trade = Trade(
            symbol="DOGE/USDT",
            strategy="DOGE_RR25",
            side=t["side"],
            entry_price=t["entry"],
            stop_loss=t["sl"],
            take_profit=t["tp"],
            status="CLOSED",
            entry_time=datetime.fromtimestamp(t["time"])
        )
        db.add(trade)
        
    for t in sol_trades:
        trade = Trade(
            symbol="SOL/USDT",
            strategy="SOL_GOD_MODE",
            side=t["side"],
            entry_price=t["entry"],
            stop_loss=t["sl"],
            take_profit=t["tp"],
            status="CLOSED",
            entry_time=datetime.fromtimestamp(t["time"])
        )
        db.add(trade)
        
    db.commit()
    db.close()
    print("Database populated successfully!")

if __name__ == "__main__":
    asyncio.run(main())
