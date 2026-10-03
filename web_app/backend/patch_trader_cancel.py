import re

with open("engine/trader.py", "r") as f:
    content = f.read()

old_execute = """        self.log(f"[{symbol}] Signal detected! Executing {side}. Entry: {entry_price}, SL: {sl_price}, TP: {tp_price}, Size: {position_size} (Leverage: {required_leverage}x)")
        
        # Execute the order on Binance
        if self.exchange.api_key and self.exchange.secret_key:
            self.log(f"[{symbol}] API keys found. Sending orders to Binance...")
            # Set the leverage before opening the order"""

new_execute = """        self.log(f"[{symbol}] Signal detected! Executing {side}. Entry: {entry_price}, SL: {sl_price}, TP: {tp_price}, Size: {position_size} (Leverage: {required_leverage}x)")
        
        # Execute the order on Binance
        if self.exchange.api_key and self.exchange.secret_key:
            self.log(f"[{symbol}] API keys found. Sending orders to Binance...")
            
            # Xóa hết lệnh hiện tại để phòng rủi ro trước khi vào lệnh mới
            try:
                self.log(f"[{symbol}] Canceling all existing open orders before entry...")
                await self.exchange.exchange.fapiPrivateDeleteAllOpenOrders({'symbol': symbol.replace('/', '')})
                await self.exchange.exchange.fapiPrivateDeleteAlgoOpenOrders({'symbol': symbol.replace('/', '')})
            except Exception as e:
                pass
                
            # Set the leverage before opening the order"""

content = content.replace(old_execute, new_execute)

# Implement manage_open_trades
manage_open_trades = """
    async def manage_open_trades(self):
        db = SessionLocal()
        open_trades = db.query(Trade).filter(Trade.status == "OPEN").all()
        if not open_trades:
            db.close()
            return
            
        try:
            # Lấy danh sách lệnh đang chờ
            open_orders = await self.exchange.exchange.fapiPrivateGetOpenOrders()
            # Lấy vị thế hiện tại
            positions = await self.exchange.exchange.fapiPrivateGetPositionRisk()
        except Exception as e:
            self.log(f"Error fetching Binance status in manage_open_trades: {e}", "ERROR")
            db.close()
            return
            
        for trade in open_trades:
            symbol_raw = trade.symbol.replace('/', '')
            # Tìm xem có lệnh chờ nào của cặp này không
            orders_for_symbol = [o for o in open_orders if o['symbol'] == symbol_raw]
            
            # Kiểm tra xem có đang có vị thế (position) không
            position_side = "LONG" if trade.side == "LONG" else "SHORT"
            pos = next((p for p in positions if p['symbol'] == symbol_raw and p['positionSide'] == position_side), None)
            
            position_amt = float(pos['positionAmt']) if pos else 0.0
            
            # Nếu vị thế = 0 và không còn lệnh chờ nào -> Lệnh đã kết thúc (Cắn SL/TP hoặc bị hủy)
            if position_amt == 0 and len(orders_for_symbol) == 0:
                self.log(f"[{trade.symbol}] Trade {trade.side} has been CLOSED/CANCELED.")
                trade.status = "CLOSED"
                trade.exit_time = datetime.now()
                # Có thể gọi API hủy tất cả lệnh 1 lần nữa để dọn rác
                try:
                    await self.exchange.exchange.fapiPrivateDeleteAllOpenOrders({'symbol': symbol_raw})
                    await self.exchange.exchange.fapiPrivateDeleteAlgoOpenOrders({'symbol': symbol_raw})
                except:
                    pass
            
            # Nếu vị thế = 0 nhưng vẫn CÒN lệnh chờ (Ví dụ: cắn SL rồi nhưng lệnh TP vẫn còn treo)
            elif position_amt == 0 and len(orders_for_symbol) > 0:
                # Kiểm tra xem lệnh Limit Entry còn treo không (chưa vào được lệnh)
                is_entry_unfilled = any(o['type'] == 'LIMIT' and o['side'] == ('BUY' if trade.side == 'LONG' else 'SELL') for o in orders_for_symbol)
                
                if not is_entry_unfilled:
                    # Đã vào lệnh xong, và giờ vị thế = 0 -> Đã cắn SL hoặc TP!
                    self.log(f"[{trade.symbol}] Hit SL/TP! Canceling remaining leftover orders...")
                    try:
                        await self.exchange.exchange.fapiPrivateDeleteAllOpenOrders({'symbol': symbol_raw})
                        await self.exchange.exchange.fapiPrivateDeleteAlgoOpenOrders({'symbol': symbol_raw})
                    except:
                        pass
                    trade.status = "CLOSED"
                    trade.exit_time = datetime.now()

        db.commit()
        db.close()
"""
if "def manage_open_trades" not in content:
    content = content.replace("    async def on_candle_closed(self):", manage_open_trades + "\n    async def on_candle_closed(self):")

with open("engine/trader.py", "w") as f:
    f.write(content)
print("Trader Cancel patched!")
