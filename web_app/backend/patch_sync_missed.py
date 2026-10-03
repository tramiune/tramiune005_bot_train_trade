import re

with open("web_app/backend/engine/trader.py", "r") as f:
    content = f.read()

old_sync = """    async def sync_missed_trades(self):
        self.log("Syncing missed trades for DOGE_3M_DEGEN...")
        try:
            # Fetch last 15 days of 3m candles (approx 7200 candles)
            ohlcv = await self.exchange.fetch_ohlcv('DOGE/USDT', '3m', limit=7200)
            if not ohlcv:
                return
                
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            signals = get_all_doge_degen_signals(df)
            
            db = SessionLocal()
            last_trade = db.query(Trade).filter(Trade.strategy == "DOGE_3M_DEGEN").order_by(Trade.entry_time.desc()).first()
            last_trade_time = pd.to_datetime(last_trade.exit_time) if (last_trade and last_trade.exit_time) else (pd.to_datetime(last_trade.entry_time) if last_trade else pd.Timestamp('2000-01-01'))
            
            if last_trade and last_trade.status == "OPEN":
                self.log("Auto-Sync skipped: A trade is currently OPEN.")
                db.close()
                return
                
            added = 0
            for sig in signals:
                entry_time = pd.to_datetime(sig['time'], unit='ms')
                if entry_time <= last_trade_time:
                    continue
                    
                entry_price = float(sig['entry_price'])
                side = sig['side']
                sl_price = entry_price * (1 + 0.15) if side == 'SHORT' else entry_price * (1 - 0.15)
                tp_price = entry_price * (1 - 0.05) if side == 'SHORT' else entry_price * (1 + 0.05)
                
                # Convert UTC to local naive (using simple timedelta or tz_convert)
                local_dt = entry_time.tz_localize('UTC').tz_convert('Asia/Ho_Chi_Minh').tz_localize(None)
                
                trade = Trade(
                    symbol="DOGE/USDT",
                    strategy="DOGE_3M_DEGEN",
                    side=side,
                    entry_time=local_dt.to_pydatetime(),
                    entry_price=entry_price,
                    stop_loss=sl_price,
                    take_profit=tp_price,
                    status="OPEN"
                )
                db.add(trade)
                added += 1
                
            if added > 0:
                db.commit()
                self.log(f"Auto-Sync complete! Recovered {added} missed trades.")
            else:
                self.log("Auto-Sync complete. No missed trades found.")
                
        except Exception as e:
            self.log(f"Auto-Sync error: {e}", "ERROR")
        finally:
            db.close()"""

new_sync = """    async def sync_missed_trades(self):
        self.log("Syncing missed trades for DOGE_3M_DEGEN...")
        try:
            from kline_cache import KLINES_CACHE
            cache_key = "DOGEUSDT_3m"
            if cache_key not in KLINES_CACHE:
                return
                
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
            db.close()"""

content = content.replace(old_sync, new_sync)
with open("web_app/backend/engine/trader.py", "w") as f:
    f.write(content)
