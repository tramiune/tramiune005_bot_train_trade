import re

with open("web_app/backend/engine/trader.py", "r") as f:
    content = f.read()

# We need to add the logic inside the trade loop in manage_open_trades
# The loop looks like:
#                for candle in ohlcv:
#                    c_time, c_open, c_high, c_low, c_close, c_vol = candle
#                    
#                    if trade.side == 'LONG':
#                        if c_low <= trade.stop_loss:

old_loop = """                # Check candles
                for candle in ohlcv:
                    c_time, c_open, c_high, c_low, c_close, c_vol = candle
                    
                    if trade.side == 'LONG':
                        if c_low <= trade.stop_loss:
                            trade.status = "CLOSED"
                            trade.exit_price = trade.stop_loss
                            trade.pnl = -1
                            trade.exit_time = pd.to_datetime(c_time, unit='ms').tz_localize('UTC').tz_convert('Asia/Ho_Chi_Minh').tz_localize(None).to_pydatetime()
                            self.log(f"Trade {trade.id} hit SL!")
                            break
                        elif c_high >= trade.take_profit:
                            trade.status = "CLOSED"
                            trade.exit_price = trade.take_profit
                            trade.pnl = 1
                            trade.exit_time = pd.to_datetime(c_time, unit='ms').tz_localize('UTC').tz_convert('Asia/Ho_Chi_Minh').tz_localize(None).to_pydatetime()
                            self.log(f"Trade {trade.id} hit TP!")
                            break
                    else:
                        if c_high >= trade.stop_loss:
                            trade.status = "CLOSED"
                            trade.exit_price = trade.stop_loss
                            trade.pnl = -1
                            trade.exit_time = pd.to_datetime(c_time, unit='ms').tz_localize('UTC').tz_convert('Asia/Ho_Chi_Minh').tz_localize(None).to_pydatetime()
                            self.log(f"Trade {trade.id} hit SL!")
                            break
                        elif c_low <= trade.take_profit:
                            trade.status = "CLOSED"
                            trade.exit_price = trade.take_profit
                            trade.pnl = 1
                            trade.exit_time = pd.to_datetime(c_time, unit='ms').tz_localize('UTC').tz_convert('Asia/Ho_Chi_Minh').tz_localize(None).to_pydatetime()
                            self.log(f"Trade {trade.id} hit TP!")
                            break"""

new_loop = """                # Check if the limit order is still open (unfilled)
                open_orders = await self.exchange.exchange.fetch_open_orders(trade.symbol)
                is_unfilled = any(
                    o['side'].upper() == trade.side.upper() 
                    and o['type'] == 'limit' 
                    and abs(o['price'] - trade.entry_price) / trade.entry_price < 0.001 
                    for o in open_orders
                )
                
                # Check candles for SL/TP hit
                hit_sl_tp = False
                hit_time = None
                hit_price = 0
                pnl = 0
                
                for candle in ohlcv:
                    c_time, c_open, c_high, c_low, c_close, c_vol = candle
                    if trade.side == 'LONG':
                        if c_low <= trade.stop_loss:
                            hit_sl_tp = True; hit_price = trade.stop_loss; pnl = -1; hit_time = c_time; break
                        elif c_high >= trade.take_profit:
                            hit_sl_tp = True; hit_price = trade.take_profit; pnl = 1; hit_time = c_time; break
                    else:
                        if c_high >= trade.stop_loss:
                            hit_sl_tp = True; hit_price = trade.stop_loss; pnl = -1; hit_time = c_time; break
                        elif c_low <= trade.take_profit:
                            hit_sl_tp = True; hit_price = trade.take_profit; pnl = 1; hit_time = c_time; break
                            
                if hit_sl_tp:
                    if is_unfilled:
                        # Price hit SL/TP BEFORE the Limit order filled! CANCEL IT!
                        self.log(f"Trade {trade.id} hit SL/TP but limit order never filled! Canceling...")
                        await self.exchange.exchange.cancel_all_orders(trade.symbol)
                        trade.status = "CANCELED"
                        trade.pnl = 0
                        trade.exit_price = hit_price
                        trade.exit_time = pd.to_datetime(hit_time, unit='ms').tz_localize('UTC').tz_convert('Asia/Ho_Chi_Minh').tz_localize(None).to_pydatetime()
                    else:
                        # Price hit SL/TP and the limit order was already filled.
                        self.log(f"Trade {trade.id} completed! Hit {'TP' if pnl > 0 else 'SL'}.")
                        trade.status = "CLOSED"
                        trade.pnl = pnl
                        trade.exit_price = hit_price
                        trade.exit_time = pd.to_datetime(hit_time, unit='ms').tz_localize('UTC').tz_convert('Asia/Ho_Chi_Minh').tz_localize(None).to_pydatetime()"""

content = content.replace(old_loop, new_loop)

with open("web_app/backend/engine/trader.py", "w") as f:
    f.write(content)
