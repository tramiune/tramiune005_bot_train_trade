import asyncio
import pandas as pd
from database import engine, SessionLocal
from models import Trade, BotConfig
from engine.backtester import backtest_doge_3m_degen
from datetime import datetime

def main():
    db = SessionLocal()
    
    print("Loading DOGE 3m Futures data from local DB...")
    df_doge = pd.read_sql("SELECT * FROM klines_dogeusdt_3m ORDER BY time ASC", engine)
    
    # The backtester expects 'timestamp', we have 'time' (in seconds)
    df_doge = df_doge.rename(columns={'time': 'timestamp'})
    df_doge['timestamp'] = df_doge['timestamp'] * 1000
    
    print(f"Loaded {len(df_doge)} candles. Running backtester...")
    doge_trades = backtest_doge_3m_degen(df_doge)
    
    print(f"Found {len(doge_trades)} DOGE 3m trades.")
    
    print("Clearing old trades and configs...")
    # Keep settings, only clear trades and config
    db.query(Trade).delete()
    db.query(BotConfig).delete()
    
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
    print("Database populated successfully with Futures trades!")

if __name__ == "__main__":
    main()
