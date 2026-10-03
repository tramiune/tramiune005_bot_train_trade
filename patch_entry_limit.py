import re

with open("web_app/backend/engine/exchange.py", "r") as f:
    content = f.read()

old_def = "async def execute_full_trade(self, symbol: str, side: str, amount: float, sl_price: float, tp_price: float):"
new_def = "async def execute_full_trade(self, symbol: str, side: str, amount: float, entry_price: float, sl_price: float, tp_price: float):"
content = content.replace(old_def, new_def)

# Restore and modify the logic
old_exec = """            # 2. Limit Entry Order (Instead of Market)
            # The user wants to place a Limit order at the exact signal price.
            # But wait, where do we get the entry_price from? 
            # execute_full_trade needs entry_price!"""

new_exec = """            formatted_entry = float(self.exchange.price_to_precision(symbol, entry_price))
            
            # 2. Limit Entry Order (Instead of Market)
            print(f"Placing ENTRY Limit {side} for {formatted_amount} {symbol} at {formatted_entry}")
            entry_order = await self.exchange.create_order(symbol, 'limit', side, formatted_amount, formatted_entry)
            
            # 3. Determine opposite side for SL/TP
            close_side = 'sell' if side == 'buy' else 'buy'"""
            
content = content.replace(old_exec, new_exec)

with open("web_app/backend/engine/exchange.py", "w") as f:
    f.write(content)

# Now patch trader.py
with open("web_app/backend/engine/trader.py", "r") as f:
    trader_content = f.read()

old_call = "await self.exchange.execute_full_trade(symbol, ccxt_side, position_size, sl_price, tp_price)"
new_call = "await self.exchange.execute_full_trade(symbol, ccxt_side, position_size, entry_price, sl_price, tp_price)"
trader_content = trader_content.replace(old_call, new_call)

with open("web_app/backend/engine/trader.py", "w") as f:
    f.write(trader_content)
