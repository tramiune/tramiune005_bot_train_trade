import ccxt.async_support as ccxt_async
import os
from dotenv import load_dotenv

load_dotenv()

class BinanceFutures:
    def __init__(self):
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
        })
            
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

    async def close_position(self, symbol: str):
        """Cancels all open orders and closes any open position for the symbol with a MARKET order."""
        try:
            await self.load_markets()
            symbol_raw = symbol.replace('/', '')
            if self.is_hedge_mode is None:
                try:
                    res = await self.exchange.fapiPrivateGetPositionSideDual()
                    self.is_hedge_mode = res.get('dualSidePosition', False)
                except Exception:
                    self.is_hedge_mode = False
                    
            # 1. Cancel all resting orders
            try:
                await self.exchange.fapiPrivateDeleteAllOpenOrders({'symbol': symbol_raw})
                await self.exchange.fapiPrivateDeleteAlgoOpenOrders({'symbol': symbol_raw})
            except Exception:
                pass
                
            # 2. Check position
            positions = await self.exchange.fapiPrivateV2GetPositionRisk()
            for p in positions:
                if p['symbol'] == symbol_raw:
                    amt = float(p['positionAmt'])
                    if abs(amt) > 0:
                        close_side = 'sell' if amt > 0 else 'buy'
                        close_amt = float(self.exchange.amount_to_precision(symbol, abs(amt)))
                        params = {}
                        if self.is_hedge_mode:
                            params['positionSide'] = p['positionSide']
                        else:
                            params['reduceOnly'] = True
                        print(f"[{symbol}] Closing open {p['positionSide']} position of {close_amt} via MARKET {close_side}...")
                        await self.exchange.create_order(symbol, 'market', close_side, close_amt, params=params)
        except Exception as e:
            print(f"[{symbol}] Error closing position: {e}")

    async def execute_full_trade(self, symbol: str, side: str, amount: float, entry_price: float, sl_price: float, tp_price: float):
        try:
            await self.load_markets()
            
            if self.is_hedge_mode is None:
                try:
                    res = await self.exchange.fapiPrivateGetPositionSideDual()
                    self.is_hedge_mode = res.get('dualSidePosition', False)
                except Exception:
                    self.is_hedge_mode = False
            
            # 1. Format precisions
            formatted_amount = float(self.exchange.amount_to_precision(symbol, amount))
            formatted_sl = float(self.exchange.price_to_precision(symbol, sl_price))
            formatted_tp = float(self.exchange.price_to_precision(symbol, tp_price)) if tp_price > 0 else 0.0
            formatted_entry = float(self.exchange.price_to_precision(symbol, entry_price))
            
            # 2. Limit Entry Order (Exact as DOGE)
            print(f"Placing ENTRY Limit {side} for {formatted_amount} {symbol} at {formatted_entry}")
            
            entry_params = {}
            if self.is_hedge_mode:
                entry_params['positionSide'] = 'LONG' if side == 'buy' else 'SHORT'
                
            entry_order = await self.exchange.create_order(symbol, 'limit', side, formatted_amount, formatted_entry, params=entry_params)
            
            # 3. Determine opposite side for SL/TP
            close_side = 'sell' if side == 'buy' else 'buy'
            
            # 4. Stop Loss Order
            print(f"Placing STOP_MARKET {close_side} at {formatted_sl}")
            sl_params = {'stopPrice': formatted_sl}
            if self.is_hedge_mode:
                sl_params['positionSide'] = 'LONG' if close_side == 'sell' else 'SHORT'
            else:
                sl_params['reduceOnly'] = True
            await self.exchange.create_order(symbol, 'STOP_MARKET', close_side, formatted_amount, params=sl_params)
            
            # 5. Take Profit Order (if specified and realistic)
            if tp_price > 0 and abs(tp_price - entry_price) / entry_price < 2.0:
                print(f"Placing TAKE_PROFIT_MARKET {close_side} at {formatted_tp}")
                tp_params = {'stopPrice': formatted_tp}
                if self.is_hedge_mode:
                    tp_params['positionSide'] = 'LONG' if close_side == 'sell' else 'SHORT'
                else:
                    tp_params['reduceOnly'] = True
                await self.exchange.create_order(symbol, 'TAKE_PROFIT_MARKET', close_side, formatted_amount, params=tp_params)
            
            return entry_order
        except Exception as e:
            print(f"Error executing full trade on Binance: {e}")
            return None
