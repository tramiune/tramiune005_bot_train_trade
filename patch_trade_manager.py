import re

with open("web_app/backend/engine/trader.py", "r") as f:
    content = f.read()

new_func = """
    async def manage_open_trades(self):
        db = SessionLocal()
        open_trades = db.query(Trade).filter(Trade.status == "OPEN").all()
        if not open_trades:
            db.close()
            return
            
        try:
            # We just need the latest candles to check if TP/SL was hit.
            # For simplicity, we just fetch recent 1m candles for each symbol.
            symbols = list(set([t.symbol for t in open_trades]))
            prices = {}
            for sym in symbols:
                ohlcv = await self.exchange.fetch_ohlcv(sym, '1m', limit=10)
                if ohlcv:
                    prices[sym] = ohlcv
                    
            for trade in open_trades:
                if trade.symbol not in prices:
                    continue
                
                # Check recent candles
                for candle in prices[trade.symbol]:
                    c_time, c_open, c_high, c_low, c_close, c_vol = candle
                    
                    if trade.side == 'LONG':
                        if c_low <= trade.stop_loss:
                            trade.status = "CLOSED"
                            trade.exit_price = trade.stop_loss
                            trade.pnl = -1
                            trade.exit_time = pd.to_datetime(c_time, unit='ms').to_pydatetime()
                            self.log(f"Trade {trade.id} hit SL!")
                            break
                        elif c_high >= trade.take_profit:
                            trade.status = "CLOSED"
                            trade.exit_price = trade.take_profit
                            trade.pnl = 1
                            trade.exit_time = pd.to_datetime(c_time, unit='ms').to_pydatetime()
                            self.log(f"Trade {trade.id} hit TP!")
                            break
                    else:
                        if c_high >= trade.stop_loss:
                            trade.status = "CLOSED"
                            trade.exit_price = trade.stop_loss
                            trade.pnl = -1
                            trade.exit_time = pd.to_datetime(c_time, unit='ms').to_pydatetime()
                            self.log(f"Trade {trade.id} hit SL!")
                            break
                        elif c_low <= trade.take_profit:
                            trade.status = "CLOSED"
                            trade.exit_price = trade.take_profit
                            trade.pnl = 1
                            trade.exit_time = pd.to_datetime(c_time, unit='ms').to_pydatetime()
                            self.log(f"Trade {trade.id} hit TP!")
                            break
            
            db.commit()
        except Exception as e:
            self.log(f"Error managing open trades: {e}", "ERROR")
        finally:
            db.close()
            
    async def run_loop"""

content = content.replace("    async def run_loop", new_func)

loop_logic = """        # Main Engine Loop
        while self.is_running:
            # Poll every 30s
            await asyncio.sleep(30)
            
            await self.manage_open_trades()
            
            configs = await self.get_active_configs()"""

content = content.replace("""        # Main Engine Loop
        while self.is_running:
            # Poll every 30s
            await asyncio.sleep(30)
            
            configs = await self.get_active_configs()""", loop_logic)

with open("web_app/backend/engine/trader.py", "w") as f:
    f.write(content)
