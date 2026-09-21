from dotenv import load_dotenv
load_dotenv()
import logging
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database import engine, Base, get_db
from models import Trade, SystemLog, BotConfig
from engine.trader import TradingEngine
from contextlib import asynccontextmanager
from fetch_more import fetch_lots_of_klines
import ccxt.async_support as ccxt
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

engine_instance = TradingEngine()

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    import asyncio
    engine_instance.is_running = True
    asyncio.create_task(engine_instance.run_loop())
    yield
    engine_instance.stop()
    await engine_instance.exchange.close()

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/status")
def get_status():
    return {"status": "RUNNING" if engine_instance.is_running else "STOPPED"}

@app.post("/api/start")
async def start_bot():
    if not engine_instance.is_running:
        import asyncio
        engine_instance.is_running = True
        asyncio.create_task(engine_instance.run_loop())
    return {"status": "RUNNING"}

@app.post("/api/stop")
async def stop_bot():
    if engine_instance.is_running:
        engine_instance.stop()
    return {"status": "STOPPED"}

@app.get("/api/trades")
def get_trades(db: Session = Depends(get_db)):
    return db.query(Trade).order_by(Trade.entry_time.desc()).limit(50).all()

@app.get("/api/configs")
def get_configs(db: Session = Depends(get_db)):
    return db.query(BotConfig).all()

@app.get("/api/backtest")
async def run_backtest(symbol: str, db: Session = Depends(get_db)):
    import pandas as pd
    
    # 1. Check if we already have trades for this symbol in SQLite
    trades = db.query(Trade).filter(Trade.symbol == symbol).order_by(Trade.entry_time.asc()).all()
    
    # 2. If NO TRADES exist in DB for this symbol, we LAZY LOAD (Calculate Backtest & Save)
    if not trades:
        logging.info(f"No historical trades found for {symbol} in DB. Lazy loading 35,000 candles from Binance...")
        try:
            data = await fetch_lots_of_klines(engine_instance.exchange.exchange, symbol, '1h', 35000)
            df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            backtest_results = []
            strategy_name = ""
            if symbol == "DOGE/USDT":
                from engine.backtester import backtest_doge_rr25
                backtest_results = backtest_doge_rr25(df)
                strategy_name = "DOGE_RR25"
            elif symbol == "SOL/USDT":
                from engine.backtester import backtest_sol_god_mode
                btc_data = await fetch_lots_of_klines(engine_instance.exchange.exchange, "BTC/USDT", '1h', 35000)
                btc_df = pd.DataFrame(btc_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                backtest_results = backtest_sol_god_mode(df, btc_df)
                strategy_name = "SOL_GOD_MODE"
            elif symbol == "BTC/USDT":
                from engine.backtester import backtest_btc_rr2
                from engine.indicators import calculate_atr
                df["atr14"] = calculate_atr(df, 14)
                backtest_results = backtest_btc_rr2(df)
                strategy_name = "BTC_RR2"

            
            # Save newly calculated backtest trades to SQLite
            logging.info(f"Calculated {len(backtest_results)} trades. Saving to SQLite...")
            for t in backtest_results:
                trade = Trade(
                    symbol=symbol,
                    strategy=strategy_name,
                    side=t["side"],
                    entry_price=t["entry"],
                    stop_loss=t["sl"],
                    take_profit=t["tp"],
                    status="CLOSED",
                    entry_time=datetime.fromtimestamp(t["time"]),
                    exit_time=datetime.fromtimestamp(t.get("exit_time", t["time"]))
                )
                db.add(trade)
            db.commit()
            
            # Fetch again after saving
            trades = db.query(Trade).filter(Trade.symbol == symbol).order_by(Trade.entry_time.asc()).all()
            
        except Exception as e:
            logging.error(f"Lazy load backtest error: {e}")
            db.rollback()

    # 3. Return the Data from SQLite
    result = []
    for t in trades:
        result.append({
            "time": t.entry_time.timestamp(),
            "side": t.side,
            "entry": t.entry_price,
            "sl": t.stop_loss,
            "tp": t.take_profit,
            "exit_time": t.exit_time.timestamp() if t.exit_time else t.entry_time.timestamp()
        })
    return result
