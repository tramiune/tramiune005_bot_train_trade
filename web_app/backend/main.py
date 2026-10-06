from dotenv import load_dotenv
load_dotenv()
import logging
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database import engine, Base, get_db
from models import Trade, SystemLog, BotConfig, Settings
from engine.trader import TradingEngine
from contextlib import asynccontextmanager
from fetch_more import fetch_lots_of_klines
from kline_cache import prefetch_klines, KLINES_CACHE
import asyncio
import ccxt.async_support as ccxt
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

from ws_engine import trader_instance, binance_ws_loop

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    import asyncio
    # Start prefetching in background
    await prefetch_klines() # block until cache is loaded
    
    asyncio.create_task(trader_instance.start())
    asyncio.create_task(binance_ws_loop())
    
    yield
    trader_instance.stop()
    await trader_instance.exchange.close()

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


from pydantic import BaseModel
class SettingsUpdate(BaseModel):
    risk_pct: float

@app.get("/api/settings")
def get_settings(db: Session = Depends(get_db)):
    settings = db.query(Settings).first()
    if not settings:
        settings = Settings(risk_pct=30.0)
        db.add(settings)
        db.commit()
    return {"risk_pct": settings.risk_pct}

@app.post("/api/settings")
def update_settings(data: SettingsUpdate, db: Session = Depends(get_db)):
    settings = db.query(Settings).first()
    if not settings:
        settings = Settings(risk_pct=data.risk_pct)
        db.add(settings)
    else:
        settings.risk_pct = data.risk_pct
    db.commit()
    return {"status": "ok"}

@app.get("/api/status")
def get_status():
    return {"status": "RUNNING" if trader_instance.is_running else "STOPPED"}

@app.post("/api/start")
async def start_bot():
    if not trader_instance.is_running:
        trader_instance.is_running = True
        trader_instance.log("Trading Engine set to ACTIVE (Will execute new trades).")
    return {"status": "RUNNING"}

@app.post("/api/stop")
async def stop_bot():
    if trader_instance.is_running:
        trader_instance.stop()
    return {"status": "STOPPED"}

from pydantic import BaseModel
from typing import Optional

class TestOrderRequest(BaseModel):
    entry_price: Optional[float] = None
    side: Optional[str] = "LONG"

@app.post("/api/test_order")
async def test_order(req: Optional[TestOrderRequest] = None):
    try:
        side = req.side if req and req.side else "LONG"
        price = req.entry_price if req and req.entry_price and req.entry_price > 0 else None
        return await trader_instance.execute_test_trade(price, side)
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/cancel_orders")
async def cancel_orders():
    from engine.exchange import BinanceFutures
    import os
    exchange = BinanceFutures()
    try:
        bot_mode = os.getenv("BOT_MODE", "XRP")
        symbol = "XRP/USDT" if bot_mode == "XRP" else "SOL/USDT"
        symbol_raw = symbol.replace('/', '')
        
        # 1. Close open position & cancel all resting orders
        await exchange.close_position(symbol)
        
        # 2. Also ensure all algo orders are cancelled
        try:
            await exchange.exchange.fapiPrivateDeleteAlgoOpenOrders({'symbol': symbol_raw})
        except Exception:
            pass
            
        # 3. Mark DB trades as CLOSED
        from database import SessionLocal
        from models import Trade
        from datetime import datetime
        db = SessionLocal()
        open_trades = db.query(Trade).filter(Trade.symbol == symbol, Trade.status == "OPEN").all()
        for t in open_trades:
            t.status = "CLOSED"
            t.exit_time = datetime.now()
        db.commit()
        db.close()
        
        return {"status": "ok", "message": f"Đã đóng vị thế và hủy toàn bộ lệnh {symbol} trên Binance!"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        await exchange.close()

@app.get("/api/balance")
async def get_balance():
    from engine.exchange import BinanceFutures
    import os
    
    # Check if keys are empty strings
    api_key = os.getenv("BINANCE_API_KEY", "")
    secret = os.getenv("BINANCE_SECRET_KEY", "")
    if not api_key or not secret:
        return {"balance": 0.0, "status": "keys_missing"}
        
    engine_exchange = BinanceFutures()
    try:
        if not engine_exchange.exchange.apiKey or not engine_exchange.exchange.secret:
            return {"balance": 0.0, "status": "keys_missing"}
        
        balance = await engine_exchange.exchange.fetch_balance()
        # USDT available balance in futures wallet
        usdt_free = balance.get('USDT', {}).get('free', 0.0)
        return {"balance": usdt_free, "status": "ok"}
    except Exception as e:
        return {"balance": 0.0, "status": "error", "message": str(e)}
    finally:
        await engine_exchange.close()

@app.get("/api/telegram/status")
def get_telegram_status():
    import os
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    ready = bool(token and chat_id and chat_id != "<WILL_BE_UPDATED>")
    return {"ready": ready}

@app.get("/api/trades")
def get_trades(db: Session = Depends(get_db)):
    return db.query(Trade).order_by(Trade.entry_time.desc()).all()

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
            data = await fetch_lots_of_klines(trader_instance.exchange.exchange, symbol, '1h', 35000)
            df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            backtest_results = []
            strategy_name = ""
            if symbol == "DOGE/USDT":
                from engine.backtester import backtest_doge_rr25
                backtest_results = backtest_doge_rr25(df)
                strategy_name = "DOGE_RR25"
            elif symbol == "SOL/USDT":
                from engine.backtester import backtest_sol_god_mode
                btc_data = await fetch_lots_of_klines(trader_instance.exchange.exchange, "BTC/USDT", '1h', 35000)
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

@app.get("/api/klines")
def get_klines(symbol: str, interval: str, limit: int = 1000, endTime: int = None):
    cache_key = f"{symbol}_{interval}"
    
    if cache_key not in KLINES_CACHE:
        # Fallback to direct fetch if cache is still building
        import ccxt
        exchange = ccxt.binance({'options': {'defaultType': 'future'}})
        params = {}
        if endTime:
            params['endTime'] = endTime
        ohlcv = exchange.fetch_ohlcv(symbol.replace('USDT', '/USDT'), interval, limit=limit, params=params)
        formatted = [{"time": int(d[0] / 1000), "open": float(d[1]), "high": float(d[2]), "low": float(d[3]), "close": float(d[4]), "volume": float(d[5])} for d in ohlcv]
        return {"status": "success", "data": formatted}
        
    data = KLINES_CACHE[cache_key]
    
    if endTime:
        # Find index where time <= endTime/1000
        # Data is sorted ascending
        target = endTime / 1000
        
        # Older than what the in-memory cache holds -> read from SQLite (table name derived from a
        # cache key that already exists, so it cannot be injected through query params)
        if data and target <= data[0]['time']:
            from sqlalchemy import text
            table_name = f"klines_{symbol.lower()}_{interval}"
            with engine.connect() as conn:
                rows = conn.execute(
                    text(f"SELECT time, open, high, low, close, volume FROM {table_name} WHERE time <= :t ORDER BY time DESC LIMIT :n"),
                    {"t": target, "n": limit}
                ).fetchall()
            older = [{"time": int(r[0]), "open": r[1], "high": r[2], "low": r[3], "close": r[4], "volume": r[5]} for r in reversed(rows)]
            return {"status": "success", "data": older}
        
        # Binary search for performance
        import bisect
        keys = [d['time'] for d in data]
        idx = bisect.bisect_right(keys, target)
        
        start_idx = max(0, idx - limit)
        return {"status": "success", "data": data[start_idx:idx]}
    else:
        # Return last `limit` candles
        return {"status": "success", "data": data[-limit:]}
