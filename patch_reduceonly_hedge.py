import re

with open("web_app/backend/engine/exchange.py", "r") as f:
    content = f.read()

old_order = """            # 4. Stop Loss Order
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

new_order = """            # 4. Stop Loss Order
            print(f"Placing STOP_MARKET {close_side} at {formatted_sl}")
            sl_params = {'stopPrice': formatted_sl}
            if self.is_hedge_mode:
                sl_params['positionSide'] = 'LONG' if close_side == 'sell' else 'SHORT'
            else:
                sl_params['reduceOnly'] = True
            await self.exchange.create_order(symbol, 'STOP_MARKET', close_side, formatted_amount, params=sl_params)
            
            # 5. Take Profit Order
            print(f"Placing TAKE_PROFIT_MARKET {close_side} at {formatted_tp}")
            tp_params = {'stopPrice': formatted_tp}
            if self.is_hedge_mode:
                tp_params['positionSide'] = 'LONG' if close_side == 'sell' else 'SHORT'
            else:
                tp_params['reduceOnly'] = True
            await self.exchange.create_order(symbol, 'TAKE_PROFIT_MARKET', close_side, formatted_amount, params=tp_params)"""

content = content.replace(old_order, new_order)

with open("web_app/backend/engine/exchange.py", "w") as f:
    f.write(content)

