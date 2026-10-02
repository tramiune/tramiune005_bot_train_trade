import re

with open("web_app/backend/engine/trader.py", "r") as f:
    content = f.read()

# Import the new function
content = content.replace(
    "from engine.strategies.doge_3m_degen import check_doge_degen_signal",
    "from engine.strategies.doge_3m_degen import check_doge_degen_signal, get_all_doge_degen_signals"
)

sync_func = """    async def sync_missed_trades(self):
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
            last_trade_time = pd.to_datetime(last_trade.entry_time) if last_trade else pd.Timestamp('2000-01-01')
            
            added = 0
            for sig in signals:
                entry_time = pd.to_datetime(sig['time'], unit='ms')
                if entry_time <= last_trade_time:
                    continue
                    
                entry_price = float(sig['entry_price'])
                side = sig['side']
                sl_price = entry_price * (1 + 0.15) if side == 'SHORT' else entry_price * (1 - 0.15)
                tp_price = entry_price * (1 - 0.05) if side == 'SHORT' else entry_price * (1 + 0.05)
                
                trade = Trade(
                    symbol="DOGE/USDT",
                    strategy="DOGE_3M_DEGEN",
                    side=side,
                    entry_time=entry_time.to_pydatetime(),
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
                
            db.close()
            
        except Exception as e:
            self.log(f"Error during Auto-Sync: {e}", "ERROR")

    async def run_loop"""

content = content.replace("    async def run_loop", sync_func)

# Call it in run_loop
run_loop_start = """    async def run_loop(self):
        self.is_running = True
        self.log("Trading Engine Started.")
        
        # Ensure initial DB configs
        db = SessionLocal()
        if not db.query(BotConfig).filter_by(strategy="DOGE_3M_DEGEN").first():
            db.add(BotConfig(strategy="DOGE_3M_DEGEN", is_active=True, risk_per_trade_pct=30.0))
        db.commit()
        db.close()
        
        await self.sync_missed_trades()
        
        # Main Engine Loop"""

content = content.replace("""    async def run_loop(self):
        self.is_running = True
        self.log("Trading Engine Started.")
        
        # Ensure initial DB configs
        db = SessionLocal()
        if not db.query(BotConfig).filter_by(strategy="DOGE_3M_DEGEN").first():
            db.add(BotConfig(strategy="DOGE_3M_DEGEN", is_active=True, risk_per_trade_pct=30.0))
        db.commit()
        db.close()
        
        # Main Engine Loop""", run_loop_start)

with open("web_app/backend/engine/trader.py", "w") as f:
    f.write(content)
