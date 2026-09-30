with open("backend/engine/exchange.py", "r") as f:
    content = f.read()

new_methods = """
    async def load_markets(self):
        await self.exchange.load_markets()

    async def execute_full_trade(self, symbol: str, side: str, amount: float, sl_price: float, tp_price: float):
        try:
            await self.load_markets()
            
            # 1. Format precisions
            formatted_amount = float(self.exchange.amount_to_precision(symbol, amount))
            formatted_sl = float(self.exchange.price_to_precision(symbol, sl_price))
            formatted_tp = float(self.exchange.price_to_precision(symbol, tp_price))
            
            # 2. Market Entry Order
            print(f"Placing ENTRY Market {side} for {formatted_amount} {symbol}")
            entry_order = await self.exchange.create_order(symbol, 'market', side, formatted_amount)
            
            # 3. Determine opposite side for SL/TP
            close_side = 'sell' if side == 'buy' else 'buy'
            
            # 4. Stop Loss Order
            print(f"Placing STOP_MARKET {close_side} at {formatted_sl}")
            sl_params = {'stopPrice': formatted_sl, 'reduceOnly': True}
            await self.exchange.create_order(symbol, 'STOP_MARKET', close_side, formatted_amount, params=sl_params)
            
            # 5. Take Profit Order
            print(f"Placing TAKE_PROFIT_MARKET {close_side} at {formatted_tp}")
            tp_params = {'stopPrice': formatted_tp, 'reduceOnly': True}
            await self.exchange.create_order(symbol, 'TAKE_PROFIT_MARKET', close_side, formatted_amount, params=tp_params)
            
            return entry_order
        except Exception as e:
            print(f"Error executing full trade on Binance: {e}")
            return None
"""

content = content + new_methods

with open("backend/engine/exchange.py", "w") as f:
    f.write(content)
print("Patched exchange.py")
