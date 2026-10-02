import asyncio
import pandas as pd
from database import engine, SessionLocal
from models import Trade, BotConfig
from fetch_more import fetch_lots_of_klines
from engine.backtester import backtest_doge_3m_degen
import ccxt.async_support as ccxt
from datetime import datetime

async def main():
    exchange = ccxt.binance({'enableRateLimit': True})
    db = SessionLocal()
    
    print("Fetching DOGE 3m data (approx 210,000 candles)...")
    doge_data = await fetch_lots_of_klines(exchange, "DOGE/USDT", '3m', 710000)
    df_doge = pd.DataFrame(doge_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    doge_trades = backtest_doge_3m_degen(df_doge)
    
    await exchange.close()
    
    print(f"Found {len(doge_trades)} DOGE 3m trades.")
    
    print("Clearing old trades and configs...")
    db.query(Trade).delete()
    db.query(BotConfig).delete()
    
    # Insert only DOGE 3m config
    db.add(BotConfig(strategy="DOGE_3M_DEGEN", is_active=True, risk_per_trade_pct=30.0))
    db.commit()

    print("Inserting to DB...")
    for t in doge_trades:
        trade = Trade(
            symbol="DOGE/USDT",
            strategy="DOGE_3M_DEGEN",
            side=t["side"],
            entry_price=t["entry"],
            stop_loss=t["sl"],
            take_profit=t["tp"],
            exit_price=t["exit_price"],
            pnl=t["pnl"],
            status="CLOSED",
            entry_time=datetime.fromtimestamp(t["time"]),
            exit_time=datetime.fromtimestamp(t["exit_time"])
        )
        db.add(trade)
        
    db.commit()
    db.close()
    print("Database populated successfully!")

if __name__ == "__main__":
    asyncio.run(main())
