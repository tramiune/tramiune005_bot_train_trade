import re

with open("web_app/backend/engine/trader.py", "r") as f:
    content = f.read()

old_execute = """        if risk_per_coin <= 0:
            self.log(f"[{symbol}] Invalid risk per coin: {risk_per_coin}", "ERROR")
            return
            
        position_size = risk_amount / risk_per_coin
        
        self.log(f"[{symbol}] Signal detected! Executing {side}. Entry: {entry_price}, SL: {sl_price}, TP: {tp_price}, Size: {position_size}")
        
        # Execute the order on Binance
        if self.exchange.api_key and self.exchange.secret_key:
            self.log(f"[{symbol}] API keys found. Sending orders to Binance...")
            await self.exchange.execute_full_trade(symbol, 'buy' if side == 'LONG' else 'sell', position_size, sl_price, tp_price)"""

new_execute = """        if risk_per_coin <= 0:
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
            # Set the leverage before opening the order
            try:
                await self.exchange.exchange.set_leverage(required_leverage, symbol.replace('/', ''))
                self.log(f"[{symbol}] Successfully set leverage to {required_leverage}x on Binance.")
            except Exception as e:
                self.log(f"[{symbol}] Failed to set leverage: {e}", "WARNING")
                
            await self.exchange.execute_full_trade(symbol, 'buy' if side == 'LONG' else 'sell', position_size, sl_price, tp_price)"""

content = content.replace(old_execute, new_execute)

with open("web_app/backend/engine/trader.py", "w") as f:
    f.write(content)
print("Leverage patched!")
