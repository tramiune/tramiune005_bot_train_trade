import ccxt.async_support as ccxt_async
import os
from dotenv import load_dotenv

load_dotenv()

class BinanceFutures:
    def __init__(self):
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
        })
        # if self.testnet:
        #    self.exchange.set_sandbox_mode(True)
            
    async def close(self):
        await self.exchange.close()
        
    async def fetch_ohlcv(self, symbol: str, timeframe: str = '1h', limit: int = 250):
        return await self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        
    async def get_balance(self, coin: str = 'USDT'):
        balance = await self.exchange.fetch_balance()
        if coin in balance['total']:
            return balance['total'][coin]
        return 0.0
        
    async def create_market_order(self, symbol: str, side: str, amount: float):
        # side: 'buy' or 'sell'
        try:
            order = await self.exchange.create_order(symbol, 'market', side, amount)
            return order
        except Exception as e:
            print(f"Error creating order: {e}")
            return None
            
    async def set_leverage(self, symbol: str, leverage: int):
        try:
            await self.exchange.set_leverage(leverage, symbol)
            return True
        except Exception as e:
            print(f"Error setting leverage: {e}")
            return False

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
