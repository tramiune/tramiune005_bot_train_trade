import sys

content = open("web_app/backend/engine/trader.py").read()

new_method = """
    async def execute_test_trade(self, entry_price: float, side: str = 'LONG'):
        symbol = "DOGE/USDT"
        strategy = "DOGE_3M_DEGEN"
        
        if side == 'LONG':
            sl_price = entry_price * (1 - 0.15)
            tp_price = entry_price * (1 + 0.05)
        else:
            sl_price = entry_price * (1 + 0.15)
            tp_price = entry_price * (1 - 0.05)
            
        # Fetch Settings from DB
        from models import Settings
        from database import SessionLocal
        db = SessionLocal()
        settings = db.query(Settings).first()
        db.close()
        
        current_risk_pct = settings.risk_pct if settings else 30.0

        # Calculate size based on risk
        balance = await self.exchange.get_balance('USDT')
        risk_amount = balance * (current_risk_pct / 100)
        risk_per_coin = abs(entry_price - sl_price)
        
        if risk_per_coin <= 0:
            return {"status": "error", "message": f"[{symbol}] Invalid risk per coin: {risk_per_coin}"}
            
        position_size = risk_amount / risk_per_coin
        notional_value = position_size * entry_price
        
        required_leverage = int(notional_value / balance) + 1
        required_leverage = max(1, min(required_leverage, 50))
        
        self.log(f"[{symbol}] TEST Signal detected! Executing {side}. Entry: {entry_price}, SL: {sl_price}, TP: {tp_price}, Size: {position_size} (Leverage: {required_leverage}x)")
        
        if self.exchange.api_key and self.exchange.secret_key:
            try:
                await self.exchange.exchange.fapiPrivatePostMarginType({
                    'symbol': symbol.replace('/', ''),
                    'marginType': 'CROSSED'
                })
            except Exception as e:
                pass
                
            try:
                await self.exchange.exchange.fapiPrivatePostLeverage({
                    'symbol': symbol.replace('/', ''),
                    'leverage': required_leverage
                })
            except Exception as e:
                self.log(f"[{symbol}] Failed to set leverage: {e}", "WARNING")
                
            await self.exchange.execute_full_trade(symbol, 'buy' if side == 'LONG' else 'sell', position_size, entry_price, sl_price, tp_price)
            
            # Send Telegram Notification
            msg = f"🧪 *TEST: {strategy} SIGNAL*\n"
            msg += f"**Pair:** {symbol}\n"
            msg += f"**Side:** {side}\n"
            msg += f"**Entry:** {entry_price:.5f}\n"
            msg += f"**Stop Loss:** {sl_price:.5f}\n"
            msg += f"**Take Profit:** {tp_price:.5f}\n"
            msg += f"**Size:** {position_size:.1f}\n"
            msg += f"**Leverage Used:** {required_leverage}x\n"
            msg += f"**Risk Amount:** ${risk_amount:.1f}"
            
            from engine.telegram import send_telegram_message
            send_telegram_message(msg)
            return {"status": "ok", "message": "Test lệnh đã được bắn lên Binance và Telegram!"}
        else:
            return {"status": "error", "message": "Không tìm thấy API Keys!"}

    async def execute_trade(self, symbol: str, strategy: str, risk_pct: float, df: pd.DataFrame, target_rr: float, side: str = 'LONG'):"""

content = content.replace("    async def execute_trade(self, symbol: str, strategy: str, risk_pct: float, df: pd.DataFrame, target_rr: float, side: str = 'LONG'):", new_method)

with open("web_app/backend/engine/trader.py", "w") as f:
    f.write(content)

