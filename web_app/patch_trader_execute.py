with open("backend/engine/trader.py", "r") as f:
    content = f.read()

replacement = """        self.log(f"[{symbol}] Signal detected! Executing LONG. Entry: {entry_price}, SL: {sl_price}, TP: {tp_price}, Size: {position_size}")
        
        # Execute the order on Binance (Entry + SL + TP)
        # Ensure API keys are set in .env!
        if self.exchange.api_key and self.exchange.secret_key:
            self.log(f"[{symbol}] API keys found. Sending orders to Binance...")
            await self.exchange.execute_full_trade(symbol, 'buy', position_size, sl_price, tp_price)
        else:
            self.log(f"[{symbol}] API keys NOT found. Running in PAPER TRADING mode.")
"""

# Replace the specific block
content = content.replace("""        self.log(f"[{symbol}] Signal detected! Executing LONG. Entry: {entry_price}, SL: {sl_price}, TP: {tp_price}, Size: {position_size}")
        
        # In a real system, you execute the order here and set up SL/TP orders or monitor them.
        # order = await self.exchange.create_market_order(symbol, 'buy', position_size)""", replacement)

with open("backend/engine/trader.py", "w") as f:
    f.write(content)

print("Patched trader.py")
