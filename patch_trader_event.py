import re

with open("web_app/backend/engine/trader.py", "r") as f:
    content = f.read()

# Replace run_loop with start and on_candle_closed
old_loop = """    async def run_loop(self):
        self.is_running = True
        self.log("Trading Engine Started.")
        
        # Ensure initial DB configs
        db = SessionLocal()
        if not db.query(BotConfig).filter_by(strategy="DOGE_3M_DEGEN").first():
            db.add(BotConfig(strategy="DOGE_3M_DEGEN", is_active=True, risk_per_trade_pct=30.0))
        db.commit()
        db.close()
        
        await self.sync_missed_trades()
        
        # Main Engine Loop
        while self.is_running:
            # Poll every 60s
            await asyncio.sleep(30)
            
            self.log("Waking up to check signals...")
            
            try:
                # 1. Manage existing trades
                await self.manage_open_trades()
                
                # 2. Check for new signals
                configs = await self.get_active_configs()
                for conf in configs:
                    if conf.strategy == "DOGE_3M_DEGEN":
                        from kline_cache import KLINES_CACHE
                        cache_key = "DOGEUSDT_3m"
                        if cache_key in KLINES_CACHE:
                            df = pd.DataFrame(KLINES_CACHE[cache_key])
                            
                            from research_scripts.DOGE_3M_DEGEN import prepare_data, check_entry_conditions
                            
                            df = prepare_data(df)
                            signal = check_entry_conditions(df)
                            
                            if signal:
                                await self.execute_trade(df, signal, 'DOGE/USDT', conf.risk_per_trade_pct, conf.strategy)
                                
            except Exception as e:
                self.log(f"Error in engine loop: {e}", "ERROR")"""

new_loop = """    async def start(self):
        self.is_running = True
        self.log("Trading Engine Started.")
        
        # Ensure initial DB configs
        db = SessionLocal()
        if not db.query(BotConfig).filter_by(strategy="DOGE_3M_DEGEN").first():
            db.add(BotConfig(strategy="DOGE_3M_DEGEN", is_active=True, risk_per_trade_pct=30.0))
        db.commit()
        db.close()
        
        await self.sync_missed_trades()
        self.log("Engine is now waiting for WebSocket candle close events...")

    async def on_candle_closed(self):
        if not self.is_running:
            return
            
        self.log("Candle closed event received! Running strategy...")
        try:
            # 1. Manage existing trades
            await self.manage_open_trades()
            
            # 2. Check for new signals
            configs = await self.get_active_configs()
            for conf in configs:
                if conf.strategy == "DOGE_3M_DEGEN":
                    from kline_cache import KLINES_CACHE
                    cache_key = "DOGEUSDT_3m"
                    if cache_key in KLINES_CACHE:
                        df = pd.DataFrame(KLINES_CACHE[cache_key])
                        
                        from research_scripts.DOGE_3M_DEGEN import prepare_data, check_entry_conditions
                        
                        df = prepare_data(df)
                        signal = check_entry_conditions(df)
                        
                        if signal:
                            await self.execute_trade(df, signal, 'DOGE/USDT', conf.risk_per_trade_pct, conf.strategy)
                            
        except Exception as e:
            self.log(f"Error in on_candle_closed: {e}", "ERROR")"""

content = content.replace(old_loop, new_loop)

with open("web_app/backend/engine/trader.py", "w") as f:
    f.write(content)
