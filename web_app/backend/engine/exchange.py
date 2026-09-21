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
