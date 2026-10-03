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
        
    async def execute_trade(self, symbol: str, strategy: str, risk_pct: float, df: pd.DataFrame, target_rr: float, side: str = 'LONG'):
        entry_price = float(df["close"].iloc[-2])
        
        if strategy == "XRP_PURE_ROBUST":
            # Fixed SL 3.0% and TP 1.5%
            sl_price = entry_price * (1 - 0.03)
            tp_price = entry_price * (1 + 0.015)
        elif strategy == "DOGE_3M_DEGEN":
            if side == 'LONG':
                sl_price = entry_price * (1 - 0.15)
                tp_price = entry_price * (1 + 0.05)
            else:
                sl_price = entry_price * (1 + 0.15)
                tp_price = entry_price * (1 - 0.05)
        else:
            # Dynamic SL using ATR for older strategies
            df["atr14"] = calculate_atr(df, 14)
            atr = float(df["atr14"].iloc[-2])
            sl_price = entry_price - (2.5 * atr if strategy == 'BTC_RR2' else 1.8 * atr)
            tp_price = entry_price + (target_rr * (entry_price - sl_price))
        
        # Fetch Settings from DB
        from models import Settings
        from database import SessionLocal
        db = SessionLocal()
        settings = db.query(Settings).first()
        db.close()
        
        current_risk_pct = risk_pct if risk_pct is not None else (settings.risk_pct if settings else 30.0)

        # Calculate size based on risk
        balance = await self.exchange.get_balance('USDT')
        risk_amount = balance * (current_risk_pct / 100)
        risk_per_coin = abs(entry_price - sl_price)
        
        if risk_per_coin <= 0:
            self.log(f"[{symbol}] Invalid risk per coin: {risk_per_coin}", "ERROR")
            return
            
        position_size = risk_amount / risk_per_coin
        notional_value = position_size * entry_price
        
        # Dynamic Leverage Calculation
        required_leverage = int(notional_value / balance) + 1
        # Cap leverage between 1x and 50x to be safe
        required_leverage = max(1, min(required_leverage, 50))
        
        self.log(f"[{symbol}] Signal detected! Executing {side}. Entry: {entry_price}, SL: {sl_price}, TP: {tp_price}, Size: {position_size} (Leverage: {required_leverage}x)")
        
        # Execute the order on Binance
        if self.exchange.api_key and self.exchange.secret_key:
            self.log(f"[{symbol}] API keys found. Sending orders to Binance...")
            
            # Xóa hết lệnh hiện tại để phòng rủi ro trước khi vào lệnh mới
            try:
                self.log(f"[{symbol}] Canceling all existing open orders before entry...")
                await self.exchange.exchange.fapiPrivateDeleteAllOpenOrders({'symbol': symbol.replace('/', '')})
                await self.exchange.exchange.fapiPrivateDeleteAlgoOpenOrders({'symbol': symbol.replace('/', '')})
            except Exception as e:
                pass
                
            # Set the leverage before opening the order
            try:
                await self.exchange.exchange.set_margin_mode('CROSSED', symbol.replace('/', ''))
                self.log(f"[{symbol}] Successfully set Margin Mode to CROSS.")
            except Exception as e:
                # Often throws error if already CROSS or if there are open positions, safe to ignore
                pass
                
            try:
                await self.exchange.exchange.set_leverage(required_leverage, symbol.replace('/', ''))
                self.log(f"[{symbol}] Successfully set leverage to {required_leverage}x on Binance.")
            except Exception as e:
                self.log(f"[{symbol}] Failed to set leverage: {e}", "WARNING")
                
            await self.exchange.execute_full_trade(symbol, 'buy' if side == 'LONG' else 'sell', position_size, sl_price, tp_price)
        else:
            self.log(f"[{symbol}] API keys NOT found. Running in PAPER TRADING mode.")

        message = (
            f"🚀 <b>{strategy} SIGNAL DETECTED</b>\n\n"
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
            entry_time=now_local
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
            db.close()
            
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
            positions = await self.exchange.exchange.fapiPrivateGetPositionRisk()
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

    async def on_candle_closed(self):
        self.log("Candle closed event received! Processing signals...")
        
        # 1. Manage existing trades
        await self.manage_open_trades()

        configs = await self.get_active_configs()
        active_strategies = [c.strategy for c in configs]
        
        if not active_strategies:
            return
            
        try:
            # Fetch 1h Macro data if needed
            if any(s in active_strategies for s in ["SOL_GOD_MODE", "DOGE_RR25", "BTC_RR2", "XRP_PURE_ROBUST"]):
                btc_data = await self.exchange.fetch_ohlcv("BTC/USDT", '1h', 250)
                btc_df = pd.DataFrame(btc_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                
            # 1. SOL 1h
            if "SOL_GOD_MODE" in active_strategies:
                sol_data = await self.exchange.fetch_ohlcv("SOL/USDT", '1h', 250)
                sol_df = pd.DataFrame(sol_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                signal = check_sol_signal(sol_df, btc_df)
                last_time = sol_df["timestamp"].iloc[-2]
                if signal == "LONG" and self.last_trade_time.get("SOL_GOD_MODE") != last_time:
                    self.last_trade_time["SOL_GOD_MODE"] = last_time
                    conf = next(c for c in configs if c.strategy == "SOL_GOD_MODE")
                    if self.is_running:
                        await self.execute_trade("SOL/USDT", "SOL_GOD_MODE", conf.risk_per_trade_pct, sol_df, 15.0)
                    else:
                        self.log("SOL_GOD_MODE Signal caught, but Bot is STOPPED. Ignoring execution.")
                    
            # 2. DOGE 1h (Old)
            if "DOGE_RR25" in active_strategies:
                doge_data = await self.exchange.fetch_ohlcv("DOGE/USDT", '1h', 250)
                doge_df = pd.DataFrame(doge_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                signal = check_doge_signal(doge_df)
                last_time = doge_df["timestamp"].iloc[-2]
                if signal == "LONG" and self.last_trade_time.get("DOGE_RR25") != last_time:
                    self.last_trade_time["DOGE_RR25"] = last_time
                    conf = next(c for c in configs if c.strategy == "DOGE_RR25")
                    if self.is_running:
                        await self.execute_trade("DOGE/USDT", "DOGE_RR25", conf.risk_per_trade_pct, doge_df, 25.0)
                    else:
                        self.log("DOGE_RR25 Signal caught, but Bot is STOPPED. Ignoring execution.")
                    
            # 2.5 DOGE 3m Degen
            if "DOGE_3M_DEGEN" in active_strategies:
                # Check if there's already an open trade
                db = SessionLocal()
                has_open = db.query(Trade).filter(Trade.strategy == "DOGE_3M_DEGEN", Trade.status == "OPEN").first()
                db.close()
                
                if not has_open:
                    doge_3m_data = await self.exchange.fetch_ohlcv("DOGE/USDT", '3m', 250)
                    doge_3m_df = pd.DataFrame(doge_3m_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                    signal = check_doge_degen_signal(doge_3m_df)
                    last_time = doge_3m_df["timestamp"].iloc[-2]
                    
                    if signal and self.last_trade_time.get("DOGE_3M_DEGEN") != last_time:
                        self.last_trade_time["DOGE_3M_DEGEN"] = last_time
                        conf = next(c for c in configs if c.strategy == "DOGE_3M_DEGEN")
                        if self.is_running:
                            await self.execute_trade("DOGE/USDT", "DOGE_3M_DEGEN", conf.risk_per_trade_pct, doge_3m_df, 1.0, side=signal)
                        else:
                            self.log(f"DOGE_3M_DEGEN Signal ({signal}) caught, but Bot is STOPPED. Ignoring execution.")
                    
            # 3. BTC 1h
            if "BTC_RR2" in active_strategies:
                btc_df["e20"] = btc_df["close"].ewm(span=20, adjust=False).mean()
                btc_df["e200"] = btc_df["close"].ewm(span=200, adjust=False).mean()
                signal = check_btc_signal(btc_df)
                last_time = btc_df["timestamp"].iloc[-2]
                if signal == "LONG" and self.last_trade_time.get("BTC_RR2") != last_time:
                    self.last_trade_time["BTC_RR2"] = last_time
                    conf = next(c for c in configs if c.strategy == "BTC_RR2")
                    if self.is_running:
                        await self.execute_trade("BTC/USDT", "BTC_RR2", conf.risk_per_trade_pct, btc_df, 2.0)
                    else:
                        self.log("BTC_RR2 Signal caught, but Bot is STOPPED. Ignoring execution.")
            
            # 4. XRP 5m
            if "XRP_PURE_ROBUST" in active_strategies:
                # Note: XRP uses 5m data!
                xrp_data = await self.exchange.fetch_ohlcv("XRP/USDT", '5m', 250)
                xrp_df = pd.DataFrame(xrp_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                signal = check_xrp_signal(xrp_df, btc_df) # btc_df is 1h, used for EMA200 Macro check
                last_time = xrp_df["timestamp"].iloc[-2]
                if signal == "LONG" and self.last_trade_time.get("XRP_PURE_ROBUST") != last_time:
                    self.last_trade_time["XRP_PURE_ROBUST"] = last_time
                    conf = next(c for c in configs if c.strategy == "XRP_PURE_ROBUST")
                    if self.is_running:
                        # target_rr doesn't matter for XRP since it uses Fixed SL/TP in execute_trade
                        await self.execute_trade("XRP/USDT", "XRP_PURE_ROBUST", conf.risk_per_trade_pct, xrp_df, 2.0)
                    else:
                        self.log("XRP_PURE_ROBUST Signal caught, but Bot is STOPPED. Ignoring execution.")
                    
        except Exception as e:
            self.log(f"Error in engine loop: {e}", "ERROR")

    def stop(self):
        self.is_running = False
        self.log("Trading Engine set to PASSIVE (Will catch signals but NOT execute).")
