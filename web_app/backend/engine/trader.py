import asyncio
import pandas as pd
from datetime import datetime, timezone
from engine.exchange import BinanceFutures
from engine.strategies.btc_rr2 import check_btc_signal
from engine.strategies.sol_god_mode import check_sol_signal
from engine.strategies.doge_rr25 import check_doge_signal
from engine.strategies.xrp_pure_robust import check_xrp_signal
from engine.strategies.doge_3m_degen import check_doge_degen_signal, get_all_doge_degen_signals
from engine.indicators import calculate_atr
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Trade, BotConfig, SystemLog, Settings
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
        

    async def execute_test_trade(self, entry_price: float = None, side: str = 'LONG'):
        import os
        bot_mode = os.getenv("BOT_MODE", "XRP")
        symbol = "XRP/USDT" if bot_mode == "XRP" else "SOL/USDT"
        strategy = bot_mode
        interval = "5m" if bot_mode == "XRP" else "4h"
        
        # 1. Fetch real market candle data
        data = await self.exchange.fetch_ohlcv(symbol, interval, 250)
        if not data or len(data) < 2:
            return {"status": "error", "message": f"Không thể lấy dữ liệu nến {symbol} từ sàn"}
            
        df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # 2. Determine entry price: if None or <= 0, use current live market price
        if not entry_price or entry_price <= 0:
            ticker = await self.exchange.exchange.fetch_ticker(symbol)
            entry_price = float(ticker['last'])
            
        # Ensure df["close"].iloc[-2] is the exact entry price
        df.iloc[-2, df.columns.get_loc('close')] = entry_price
        
        # 3. Read configured risk from DB
        db = SessionLocal()
        settings = db.query(Settings).first()
        db.close()
        configured_risk = float(settings.risk_pct) if settings and settings.risk_pct is not None else 10.0
        
        self.log(f"[{symbol}] Kích hoạt lệnh TEST THỦ CÔNG {side} tại giá {entry_price} (Risk: {configured_risk}%)...")
        
        # 4. Execute through the EXACT SAME pipeline as live signal
        await self.execute_trade(
            symbol=symbol,
            strategy=strategy,
            risk_pct=configured_risk,
            df=df,
            target_rr=1.0,
            side=side,
            tag=" (🧪 Test Khởi Chạy Thủ Công)"
        )
        return {"status": "ok", "message": f"Đã bắn lệnh test {side} {symbol} tại giá {entry_price:.4f} lên Binance & Telegram!"}

    async def execute_trade(self, symbol: str, strategy: str, risk_pct: float, df: pd.DataFrame, target_rr: float, side: str = 'LONG', tag: str = "", entry_time=None):
        entry_price = float(df["close"].iloc[-2])
        
        if strategy == "XRP":
            if side == 'LONG':
                sl_price = entry_price * (1 - 0.0055)
                tp_price = entry_price * (1 + 0.179)
            else:
                sl_price = entry_price * (1 + 0.0055)
                tp_price = entry_price * (1 - 0.179)
            risk_per_coin = abs(entry_price - sl_price)
        elif strategy == "SOL":
            from engine.strategies.sol_supertrend import get_sol_sl_prices
            lb, ub = get_sol_sl_prices(df)
            if side == 'LONG':
                sl_price = lb
                tp_price = 0.0 # SOL exits dynamically when trend flips
            else:
                sl_price = ub
                tp_price = 0.0
            risk_per_coin = abs(entry_price - sl_price)
        else:
            return
        # Fetch user-configured risk_pct from Settings
        db = SessionLocal()
        settings = db.query(Settings).first()
        db.close()
        if settings and settings.risk_pct is not None:
            current_risk_pct = float(settings.risk_pct)
        elif risk_pct is not None:
            current_risk_pct = float(risk_pct)
        else:
            current_risk_pct = 10.0

        balance = await self.exchange.get_balance('USDT')
        risk_amount = balance * (current_risk_pct / 100)
        
        if risk_per_coin <= 0:
            self.log(f"[{symbol}] Invalid risk per coin: {risk_per_coin}", "ERROR")
            return
            
        position_size = risk_amount / risk_per_coin
        notional_value = position_size * entry_price
        
        required_leverage = int(notional_value / balance) + 1
        required_leverage = max(1, min(required_leverage, 75))
        
        self.log(f"[{symbol}] Signal detected! Executing {side}. Entry: {entry_price}, SL: {sl_price}, TP: {tp_price}, Size: {position_size} (Leverage: {required_leverage}x)")
        
        if self.exchange.api_key and self.exchange.secret_key:
            try:
                await self.exchange.exchange.fapiPrivateDeleteAllOpenOrders({'symbol': symbol.replace('/', '')})
                await self.exchange.exchange.fapiPrivateDeleteAlgoOpenOrders({'symbol': symbol.replace('/', '')})
            except:
                pass
                
            try:
                await self.exchange.exchange.set_margin_mode('CROSSED', symbol.replace('/', ''))
                await self.exchange.exchange.set_leverage(required_leverage, symbol.replace('/', ''))
            except:
                pass
                
            await self.exchange.execute_full_trade(symbol, 'buy' if side == 'LONG' else 'sell', position_size, entry_price, sl_price, tp_price)
        else:
            self.log(f"[{symbol}] API keys NOT found. PAPER TRADING mode.")

        message = (
            f"🚀 <b>{strategy} SIGNAL DETECTED</b>{tag}\n\n"
            f"<b>Pair:</b> {symbol}\n"
            f"<b>Side:</b> {side}\n"
            f"<b>Entry:</b> {entry_price:.4f}\n"
            f"<b>Stop Loss:</b> {sl_price:.4f}\n"
            f"<b>Take Profit:</b> {tp_price:.4f}\n"
            f"<b>Risk:</b> {risk_pct}%"
        )
        
        # Log to DB
        db = SessionLocal()
        from datetime import datetime
        now_local = datetime.now() # naive local time
        trade = Trade(
            symbol=symbol,
            strategy=strategy,
            side=side,
            entry_price=entry_price,
            stop_loss=sl_price,
            take_profit=tp_price,
            size=position_size,
            status="OPEN",
            entry_time=entry_time or now_local
        )
        db.add(trade)
        db.commit()
        db.close()
        await send_telegram_message(message)
        
    async def sync_missed_trades(self):
        self.log("Syncing missed trades for DOGE_3M_DEGEN...")
        try:
            from kline_cache import KLINES_CACHE
            cache_key = "DOGEUSDT_3m"
            if cache_key not in KLINES_CACHE:
                return
                
            import pandas as pd
            df = pd.DataFrame(KLINES_CACHE[cache_key])
            df = df.rename(columns={'time': 'timestamp'})
            df['timestamp'] = df['timestamp'] * 1000
            
            from engine.backtester import backtest_doge_3m_degen
            missed_trades = backtest_doge_3m_degen(df)
            
            db = SessionLocal()
            last_trade = db.query(Trade).filter(Trade.strategy == "DOGE_3M_DEGEN").order_by(Trade.entry_time.desc()).first()
            last_trade_time = last_trade.entry_time.timestamp() if last_trade and last_trade.entry_time else 0
            
            if last_trade and last_trade.status == "OPEN":
                self.log("Auto-Sync skipped: A trade is currently OPEN.")
                db.close()
                return
                
            added = 0
            from datetime import datetime
            for t in missed_trades:
                if t['time'] <= last_trade_time:
                    continue
                    
                trade = Trade(
                    symbol="DOGE/USDT",
                    strategy="DOGE_3M_DEGEN",
                    side=t['side'],
                    entry_price=t['entry'],
                    stop_loss=t['sl'],
                    take_profit=t['tp'],
                    exit_price=t['exit_price'],
                    pnl=t['pnl'],
                    status="CLOSED",
                    entry_time=datetime.fromtimestamp(t['time']),
                    exit_time=datetime.fromtimestamp(t['exit_time'])
                )
                db.add(trade)
                added += 1
                
            if added > 0:
                db.commit()
                self.log(f"Auto-Sync complete! Recovered {added} missed closed trades.")
            else:
                self.log("Auto-Sync complete. No missed trades found.")
                
        except Exception as e:
            self.log(f"Auto-Sync error: {e}", "ERROR")
        finally:
            if db:
                db.close()
            
    async def recover_missed_signal(self):
        """If a DOGE_3M_DEGEN signal fired while the bot was down/crashed and it is still worth entering
        (see engine.recovery), enter it now through the exact same execute_trade used for live signals."""
        try:
            if not self.is_running:
                self.log("Signal recovery skipped: bot is STOPPED.")
                return

            from kline_cache import KLINES_CACHE
            data = KLINES_CACHE.get("DOGEUSDT_3m")
            if not data:
                return

            from engine.recovery import find_recoverable_signal
            df = pd.DataFrame(data).rename(columns={'time': 'timestamp'})
            df['timestamp'] = df['timestamp'] * 1000
            # The last cached row is the candle still forming -> never evaluate it
            closed = df.iloc[:-1].reset_index(drop=True)
            sig, reason = find_recoverable_signal(closed)
            if not sig:
                self.log(f"Signal recovery: nothing to enter ({reason}).")
                return

            from datetime import datetime
            signal_dt = datetime.fromtimestamp(sig['time_ms'] / 1000)
            db = SessionLocal()
            try:
                has_open = db.query(Trade).filter(Trade.strategy == "DOGE_3M_DEGEN", Trade.status == "OPEN").first()
                already = db.query(Trade).filter(Trade.strategy == "DOGE_3M_DEGEN", Trade.entry_time >= signal_dt).first()
            finally:
                db.close()
            if has_open or already:
                self.log("Signal recovery skipped: a trade is already open or was already taken for this signal.")
                return

            configs = await self.get_active_configs()
            conf = next((c for c in configs if c.strategy == "DOGE_3M_DEGEN"), None)
            if conf is None:
                return

            # df rows up to and including the candle AFTER the signal, so execute_trade's df["close"].iloc[-2]
            # is exactly the signal candle's close (same entry price as the live path would have used).
            trade_df = df.iloc[:sig['index'] + 2].copy()
            self.last_trade_time["DOGE_3M_DEGEN"] = trade_df["timestamp"].iloc[-2]
            self.log(f"Signal recovery: entering missed {sig['side']} signal ({sig['age_candles']} candles old, "
                     f"entry {sig['entry']}, price drift {sig['drift_pct']}%).")
            await self.execute_trade("DOGE/USDT", "DOGE_3M_DEGEN", conf.risk_per_trade_pct, trade_df, 1.0,
                                     side=sig['side'], tag=f" (♻️ khôi phục, tín hiệu cách {sig['age_candles'] * 3} phút)",
                                     entry_time=datetime.fromtimestamp(sig['time_ms'] / 1000 + 180))
        except Exception as e:
            self.log(f"Signal recovery error: {e}", "ERROR")

    async def start(self):
        self.is_running = True
        self.log("Trading Engine set to ACTIVE (Will execute new trades).")
        
        # Ensure initial DB configs
        db = SessionLocal()
        if not db.query(BotConfig).filter_by(strategy="DOGE_3M_DEGEN").first():
            db.add(BotConfig(strategy="DOGE_3M_DEGEN", is_active=True, risk_per_trade_pct=30.0))
        db.commit()
        db.close()
        
        await self.sync_missed_trades()
        await self.recover_missed_signal()
        self.log("Engine is now waiting for WebSocket candle close events...")


    async def manage_open_trades(self):
        db = SessionLocal()
        open_trades = db.query(Trade).filter(Trade.status == "OPEN").all()
        if not open_trades:
            db.close()
            return
            
        try:
            # Lấy danh sách lệnh đang chờ
            open_orders = await self.exchange.exchange.fapiPrivateGetOpenOrders()
            # Lấy vị thế hiện tại
            positions = await self.exchange.exchange.fapiPrivateV2GetPositionRisk()
        except Exception as e:
            self.log(f"Error fetching Binance status in manage_open_trades: {e}", "ERROR")
            db.close()
            return
            
        for trade in open_trades:
            symbol_raw = trade.symbol.replace('/', '')
            # Tìm xem có lệnh chờ nào của cặp này không
            orders_for_symbol = [o for o in open_orders if o['symbol'] == symbol_raw]
            
            # Kiểm tra xem có đang có vị thế (position) không
            position_side = "LONG" if trade.side == "LONG" else "SHORT"
            pos = next((p for p in positions if p['symbol'] == symbol_raw and p['positionSide'] == position_side), None)
            
            position_amt = float(pos['positionAmt']) if pos else 0.0
            
            # Nếu vị thế = 0 và không còn lệnh chờ nào -> Lệnh đã kết thúc (Cắn SL/TP hoặc bị hủy)
            if position_amt == 0 and len(orders_for_symbol) == 0:
                self.log(f"[{trade.symbol}] Trade {trade.side} has been CLOSED/CANCELED.")
                trade.status = "CLOSED"
                trade.exit_time = datetime.now()
                # Có thể gọi API hủy tất cả lệnh 1 lần nữa để dọn rác
                try:
                    await self.exchange.exchange.fapiPrivateDeleteAllOpenOrders({'symbol': symbol_raw})
                    await self.exchange.exchange.fapiPrivateDeleteAlgoOpenOrders({'symbol': symbol_raw})
                except:
                    pass
            
            # Nếu vị thế = 0 nhưng vẫn CÒN lệnh chờ (Ví dụ: cắn SL rồi nhưng lệnh TP vẫn còn treo)
            elif position_amt == 0 and len(orders_for_symbol) > 0:
                # Kiểm tra xem lệnh Limit Entry còn treo không (chưa vào được lệnh)
                is_entry_unfilled = any(o['type'] == 'LIMIT' and o['side'] == ('BUY' if trade.side == 'LONG' else 'SELL') for o in orders_for_symbol)
                
                if not is_entry_unfilled:
                    # Đã vào lệnh xong, và giờ vị thế = 0 -> Đã cắn SL hoặc TP!
                    self.log(f"[{trade.symbol}] Hit SL/TP! Canceling remaining leftover orders...")
                    try:
                        await self.exchange.exchange.fapiPrivateDeleteAllOpenOrders({'symbol': symbol_raw})
                        await self.exchange.exchange.fapiPrivateDeleteAlgoOpenOrders({'symbol': symbol_raw})
                    except:
                        pass
                    trade.status = "CLOSED"
                    trade.exit_time = datetime.now()

        db.commit()
        db.close()

    async def on_candle_closed(self, bot_mode="XRP"):
        self.log(f"Candle closed event received for {bot_mode}! Processing signals...")
        await self.manage_open_trades()

        try:
            db = SessionLocal()
            settings = db.query(Settings).first()
            db.close()
            configured_risk = float(settings.risk_pct) if settings and settings.risk_pct is not None else 10.0

            if bot_mode == "XRP":
                from engine.strategies.xrp_nada_final import check_xrp_signal
                xrp_data = await self.exchange.fetch_ohlcv("XRP/USDT", '5m', 1500)
                xrp_df = pd.DataFrame(xrp_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                signal = check_xrp_signal(xrp_df)
                last_time = xrp_df["timestamp"].iloc[-2]
                
                if signal in ["LONG", "SHORT"] and self.last_trade_time.get("XRP") != last_time:
                    self.last_trade_time["XRP"] = last_time
                    if self.is_running:
                        await self.execute_trade("XRP/USDT", "XRP", configured_risk, xrp_df, 1.0, side=signal)
                        
            elif bot_mode == "SOL":
                from engine.strategies.sol_supertrend import check_sol_signal
                sol_data = await self.exchange.fetch_ohlcv("SOL/USDT", '4h', 250)
                sol_df = pd.DataFrame(sol_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                signal = check_sol_signal(sol_df)
                last_time = sol_df["timestamp"].iloc[-2]
                
                if signal in ["LONG", "SHORT"] and self.last_trade_time.get("SOL") != last_time:
                    self.last_trade_time["SOL"] = last_time
                    if self.is_running:
                        self.log(f"SOL Supertrend flipped to {signal}! Closing existing positions and opening new...")
                        await self.exchange.close_position("SOL/USDT")
                        await self.execute_trade("SOL/USDT", "SOL", configured_risk, sol_df, 1.0, side=signal)
                        
        except Exception as e:
            self.log(f"Error in engine loop: {e}", "ERROR")

    def stop(self):
        self.is_running = False
        self.log("Trading Engine set to PASSIVE (Will catch signals but NOT execute).")
