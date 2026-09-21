import asyncio
import pandas as pd
from datetime import datetime, timezone
from engine.exchange import BinanceFutures
from engine.strategies.btc_rr2 import check_btc_signal
from engine.strategies.sol_god_mode import check_sol_signal
from engine.strategies.doge_rr25 import check_doge_signal
from engine.indicators import calculate_atr
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Trade, BotConfig, SystemLog
from engine.telegram import send_telegram_message


class TradingEngine:
    def __init__(self):
        self.exchange = BinanceFutures()
        self.is_running = False
        self.last_trade_time = {}
        
    def log(self, message: str, level="INFO"):
        print(f"[{datetime.now(timezone.utc).isoformat()}] {level}: {message}")
        db = SessionLocal()
        db.add(SystemLog(level=level, message=message))
        db.commit()
        db.close()
        
    async def get_active_configs(self):
        db = SessionLocal()
        configs = db.query(BotConfig).filter(BotConfig.is_active == True).all()
        db.close()
        return configs
        
    async def execute_trade(self, symbol: str, strategy: str, risk_pct: float, df: pd.DataFrame, target_rr: float):
        # Calculate ATR for SL
        df["atr14"] = calculate_atr(df, 14)
        atr = float(df["atr14"].iloc[-2])
        entry_price = float(df["close"].iloc[-2])
        
        sl_price = entry_price - (2.5 * atr if strategy == 'BTC_RR2' else 1.8 * atr)
        tp_price = entry_price + (target_rr * (entry_price - sl_price))
        
        # Calculate size based on risk
        balance = await self.exchange.get_balance('USDT')
        risk_amount = balance * (risk_pct / 100)
        risk_per_coin = entry_price - sl_price
        
        if risk_per_coin <= 0:
            self.log(f"[{symbol}] Invalid risk per coin: {risk_per_coin}", "ERROR")
            return
            
        position_size = risk_amount / risk_per_coin
        
        self.log(f"[{symbol}] Signal detected! Executing LONG. Entry: {entry_price}, SL: {sl_price}, TP: {tp_price}, Size: {position_size}")
        
        # In a real system, you execute the order here and set up SL/TP orders or monitor them.
        # order = await self.exchange.create_market_order(symbol, 'buy', position_size)
        
        
        message = (
            f"🚀 <b>{strategy} SIGNAL DETECTED</b>\n\n"
            f"<b>Pair:</b> {symbol}\n"
            f"<b>Side:</b> LONG\n"
            f"<b>Entry:</b> {entry_price:.4f}\n"
            f"<b>Stop Loss:</b> {sl_price:.4f}\n"
            f"<b>Take Profit:</b> {tp_price:.4f}\n"
            f"<b>Risk:</b> {risk_pct}%"
        )
        
        # Log to DB first
        # Log to DB
        db = SessionLocal()
        trade = Trade(
            symbol=symbol,
            strategy=strategy,
            side="LONG",
            entry_price=entry_price,
            stop_loss=sl_price,
            take_profit=tp_price,
            size=position_size,
            status="OPEN"
        )
        db.add(trade)
        db.commit()
        db.close()
        await send_telegram_message(message)
        
    async def run_loop(self):
        self.is_running = True
        self.log("Trading Engine Started.")
        
        # Ensure initial DB configs
        db = SessionLocal()
        if not db.query(BotConfig).filter_by(strategy="SOL_GOD_MODE").first():
            db.add(BotConfig(strategy="SOL_GOD_MODE", is_active=True, risk_per_trade_pct=3.0))
        if not db.query(BotConfig).filter_by(strategy="DOGE_RR25").first():
            db.add(BotConfig(strategy="DOGE_RR25", is_active=True, risk_per_trade_pct=3.0))
        if not db.query(BotConfig).filter_by(strategy="BTC_RR2").first():
            db.add(BotConfig(strategy="BTC_RR2", is_active=True, risk_per_trade_pct=3.0))
        db.commit()
        db.close()
        
        while self.is_running:
            now = datetime.now(timezone.utc)
            # Sleep until the top of the next hour
            next_hour = (now.replace(minute=0, second=0, microsecond=0) + pd.Timedelta(hours=1))
            sleep_seconds = (next_hour - now).total_seconds()
            
            # For testing purposes, if sleep is too long, we can just sleep a few seconds, but in production:
            # self.log(f"Sleeping for {sleep_seconds} seconds until next hour...")
            # await asyncio.sleep(sleep_seconds)
            
            # Actually, to make it testable, we sleep 60s in this loop and just check if we crossed an hour boundary
            # OR we can just run it once per minute for testing. Let's do 60s polling.
            await asyncio.sleep(60)
            
            configs = await self.get_active_configs()
            active_strategies = [c.strategy for c in configs]
            
            if not active_strategies:
                continue
                
            try:
                # Fetch data
                if "SOL_GOD_MODE" in active_strategies or "DOGE_RR25" in active_strategies or "BTC_RR2" in active_strategies:
                    btc_data = await self.exchange.fetch_ohlcv("BTC/USDT", '1h', 250)
                    btc_df = pd.DataFrame(btc_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                    
                if "SOL_GOD_MODE" in active_strategies:
                    sol_data = await self.exchange.fetch_ohlcv("SOL/USDT", '1h', 250)
                    sol_df = pd.DataFrame(sol_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                    signal = check_sol_signal(sol_df, btc_df)
                    last_time = sol_df["timestamp"].iloc[-2]
                    if signal == "LONG" and self.last_trade_time.get("SOL_GOD_MODE") != last_time:
                        self.last_trade_time["SOL_GOD_MODE"] = last_time
                        conf = next(c for c in configs if c.strategy == "SOL_GOD_MODE")
                        await self.execute_trade("SOL/USDT", "SOL_GOD_MODE", conf.risk_per_trade_pct, sol_df, 15.0)
                        
                if "DOGE_RR25" in active_strategies:
                    doge_data = await self.exchange.fetch_ohlcv("DOGE/USDT", '1h', 250)
                    doge_df = pd.DataFrame(doge_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                    signal = check_doge_signal(doge_df)
                    last_time = doge_df["timestamp"].iloc[-2]
                    if signal == "LONG" and self.last_trade_time.get("DOGE_RR25") != last_time:
                        self.last_trade_time["DOGE_RR25"] = last_time
                        conf = next(c for c in configs if c.strategy == "DOGE_RR25")
                        await self.execute_trade("DOGE/USDT", "DOGE_RR25", conf.risk_per_trade_pct, doge_df, 25.0)
                        
                if "BTC_RR2" in active_strategies:
                    btc_df["e20"] = btc_df["close"].ewm(span=20, adjust=False).mean()
                    btc_df["e200"] = btc_df["close"].ewm(span=200, adjust=False).mean()
                    signal = check_btc_signal(btc_df)
                    last_time = btc_df["timestamp"].iloc[-2]
                    if signal == "LONG" and self.last_trade_time.get("BTC_RR2") != last_time:
                        self.last_trade_time["BTC_RR2"] = last_time
                        conf = next(c for c in configs if c.strategy == "BTC_RR2")
                        await self.execute_trade("BTC/USDT", "BTC_RR2", conf.risk_per_trade_pct, btc_df, 2.0)
            except Exception as e:
                self.log(f"Error in engine loop: {e}", "ERROR")

    def stop(self):
        self.is_running = False
        self.log("Trading Engine Stopped.")
