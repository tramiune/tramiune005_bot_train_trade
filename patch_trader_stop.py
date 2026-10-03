import re

with open("web_app/backend/engine/trader.py", "r") as f:
    content = f.read()

# Remove the early return
old_return = """    async def on_candle_closed(self):
        if not self.is_running:
            return
            
        self.log("Candle closed event received! Running strategy...")"""

new_return = """    async def on_candle_closed(self):
        self.log("Candle closed event received! Processing...")"""

content = content.replace(old_return, new_return)

# Add the check before execute_trade
old_execute = """                        if signal:
                            await self.execute_trade(df, signal, 'DOGE/USDT', conf.risk_per_trade_pct, conf.strategy)"""

new_execute = """                        if signal:
                            if not self.is_running:
                                self.log(f"Signal {signal} caught for DOGE/USDT, but Bot is STOPPED. Ignoring execution.")
                            else:
                                await self.execute_trade(df, signal, 'DOGE/USDT', conf.risk_per_trade_pct, conf.strategy)"""

content = content.replace(old_execute, new_execute)

# Update start and stop logs
content = content.replace('self.log("Trading Engine Started.")', 'self.log("Trading Engine set to ACTIVE (Will execute new trades).")')
content = content.replace('self.log("Trading Engine Stopped.")', 'self.log("Trading Engine set to PASSIVE (Will catch signals but NOT execute).")')

with open("web_app/backend/engine/trader.py", "w") as f:
    f.write(content)
