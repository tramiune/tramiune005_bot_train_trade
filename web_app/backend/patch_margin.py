import re

with open("web_app/backend/engine/trader.py", "r") as f:
    content = f.read()

old_execute = """            try:
                await self.exchange.exchange.set_leverage(required_leverage, symbol.replace('/', ''))
                self.log(f"[{symbol}] Successfully set leverage to {required_leverage}x on Binance.")
            except Exception as e:
                self.log(f"[{symbol}] Failed to set leverage: {e}", "WARNING")"""

new_execute = """            try:
                await self.exchange.exchange.set_margin_mode('CROSSED', symbol.replace('/', ''))
                self.log(f"[{symbol}] Successfully set Margin Mode to CROSS.")
            except Exception as e:
                # Often throws error if already CROSS or if there are open positions, safe to ignore
                pass
                
            try:
                await self.exchange.exchange.set_leverage(required_leverage, symbol.replace('/', ''))
                self.log(f"[{symbol}] Successfully set leverage to {required_leverage}x on Binance.")
            except Exception as e:
                self.log(f"[{symbol}] Failed to set leverage: {e}", "WARNING")"""

content = content.replace(old_execute, new_execute)

with open("web_app/backend/engine/trader.py", "w") as f:
    f.write(content)
print("Margin patched!")
