import re

with open("web_app/backend/engine/trader.py", "r") as f:
    content = f.read()

old_logic = """        if risk_per_coin <= 0:
            self.log(f"[{symbol}] Invalid risk per coin: {risk_per_coin}", "ERROR")
            return
            
        position_size = risk_amount / risk_per_coin
        
        self.log(f"[{symbol}] Signal detected! Executing {side}. Entry: {entry_price}, SL: {sl_price}, TP: {tp_price}, Size: {position_size}")
        
        # Execute the order on Binance
        if self.exchange.api_key and self.exchange.secret_key:
            self.log(f"[{symbol}] API keys found. Sending orders to Binance...")
            await self.exchange.execute_full_trade(symbol, 'buy' if side == 'LONG' else 'sell', position_size, entry_price, sl_price, tp_price)"""

new_logic = """        if risk_per_coin <= 0:
            self.log(f"[{symbol}] Invalid risk per coin: {risk_per_coin}", "ERROR")
            return
            
        position_size = risk_amount / risk_per_coin
        
        # Auto-calculate required leverage
        notional_value = position_size * entry_price
        required_leverage = int(notional_value / balance) + 1
        
        # Bound the leverage safely between 1x and 50x (DOGE max is typically 50x-75x)
        if required_leverage < 1:
            required_leverage = 1
        if required_leverage > 50:
            self.log(f"[{symbol}] WARNING: Required leverage {required_leverage}x exceeds safe limit 50x. Capping at 50x.")
            required_leverage = 50
            
        self.log(f"[{symbol}] Signal detected! Executing {side}. Size: {position_size}. Auto-Leverage: {required_leverage}x")
        
        # Execute the order on Binance
        if self.exchange.api_key and self.exchange.secret_key:
            self.log(f"[{symbol}] Updating leverage to {required_leverage}x...")
            await self.exchange.set_leverage(symbol.replace('/', ''), required_leverage)
            
            self.log(f"[{symbol}] Sending Limit/SL/TP orders to Binance...")
            await self.exchange.execute_full_trade(symbol, 'buy' if side == 'LONG' else 'sell', position_size, entry_price, sl_price, tp_price)"""

content = content.replace(old_logic, new_logic)

with open("web_app/backend/engine/trader.py", "w") as f:
    f.write(content)
