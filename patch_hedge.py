import re

with open("web_app/backend/engine/exchange.py", "r") as f:
    content = f.read()

# Add hedge mode detection to BinanceFutures class
init_old = """    def __init__(self):
        self.api_key = os.getenv("BINANCE_API_KEY")
        self.secret_key = os.getenv("BINANCE_SECRET_KEY")
        self.testnet = os.getenv("TESTNET", "true").lower() == "true"
        
        self.exchange = ccxt_async.binance({
            'apiKey': self.api_key,
            'secret': self.secret_key,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'future'
            }
        })"""

init_new = """    def __init__(self):
        self.api_key = os.getenv("BINANCE_API_KEY")
        self.secret_key = os.getenv("BINANCE_SECRET_KEY")
        self.testnet = os.getenv("TESTNET", "true").lower() == "true"
        self.is_hedge_mode = None
        
        self.exchange = ccxt_async.binance({
            'apiKey': self.api_key,
            'secret': self.secret_key,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'future'
            }
        })"""
content = content.replace(init_old, init_new)

# Add check to execute_full_trade
exec_old = """        try:
            await self.load_markets()
            
            # 1. Format precisions"""

exec_new = """        try:
            await self.load_markets()
            
            if self.is_hedge_mode is None:
                try:
                    res = await self.exchange.fapiPrivateGetPositionSideDual()
                    self.is_hedge_mode = res.get('dualSidePosition', False)
                except Exception:
                    self.is_hedge_mode = False
            
            # 1. Format precisions"""
content = content.replace(exec_old, exec_new)

# Update the order creations to use positionSide if needed
order_old = """            # 2. Limit Entry Order (Instead of Market)
            print(f"Placing ENTRY Limit {side} for {formatted_amount} {symbol} at {formatted_entry}")
            entry_order = await self.exchange.create_order(symbol, 'limit', side, formatted_amount, formatted_entry)
            
            # 3. Determine opposite side for SL/TP
            close_side = 'sell' if side == 'buy' else 'buy'
            
            # 4. Stop Loss Order
            print(f"Placing STOP_MARKET {close_side} at {formatted_sl}")
            sl_params = {'stopPrice': formatted_sl, 'reduceOnly': True}
            await self.exchange.create_order(symbol, 'STOP_MARKET', close_side, formatted_amount, params=sl_params)
            
            # 5. Take Profit Order
            print(f"Placing TAKE_PROFIT_MARKET {close_side} at {formatted_tp}")
            tp_params = {'stopPrice': formatted_tp, 'reduceOnly': True}
            await self.exchange.create_order(symbol, 'TAKE_PROFIT_MARKET', close_side, formatted_amount, params=tp_params)"""

order_new = """            # 2. Limit Entry Order (Instead of Market)
            print(f"Placing ENTRY Limit {side} for {formatted_amount} {symbol} at {formatted_entry}")
            
            entry_params = {}
            if self.is_hedge_mode:
                entry_params['positionSide'] = 'LONG' if side == 'buy' else 'SHORT'
                
            entry_order = await self.exchange.create_order(symbol, 'limit', side, formatted_amount, formatted_entry, params=entry_params)
            
            # 3. Determine opposite side for SL/TP
            close_side = 'sell' if side == 'buy' else 'buy'
            
            # 4. Stop Loss Order
            print(f"Placing STOP_MARKET {close_side} at {formatted_sl}")
            sl_params = {'stopPrice': formatted_sl, 'reduceOnly': True}
            if self.is_hedge_mode:
                sl_params['positionSide'] = 'LONG' if close_side == 'sell' else 'SHORT'
            await self.exchange.create_order(symbol, 'STOP_MARKET', close_side, formatted_amount, params=sl_params)
            
            # 5. Take Profit Order
            print(f"Placing TAKE_PROFIT_MARKET {close_side} at {formatted_tp}")
            tp_params = {'stopPrice': formatted_tp, 'reduceOnly': True}
            if self.is_hedge_mode:
                tp_params['positionSide'] = 'LONG' if close_side == 'sell' else 'SHORT'
            await self.exchange.create_order(symbol, 'TAKE_PROFIT_MARKET', close_side, formatted_amount, params=tp_params)"""
content = content.replace(order_old, order_new)

with open("web_app/backend/engine/exchange.py", "w") as f:
    f.write(content)
