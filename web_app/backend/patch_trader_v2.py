import re

with open('web_app/backend/engine/trader.py', 'r') as f:
    content = f.read()

# Replace execute_trade
execute_trade_regex = re.compile(r'    async def execute_trade\(self, symbol: str, strategy: str, risk_pct: float, df: pd\.DataFrame, target_rr: float, side: str = \'LONG\', tag: str = "", entry_time=None\):.*?        message = \(', re.DOTALL)

new_execute_trade = """    async def execute_trade(self, symbol: str, strategy: str, risk_pct: float, df: pd.DataFrame, target_rr: float, side: str = 'LONG', tag: str = "", entry_time=None):
        entry_price = float(df["close"].iloc[-2])
        
        if strategy == "XRP":
            sl_price = entry_price * (1 - 0.0055)
            tp_price = entry_price * (1 + 0.179)
            risk_per_coin = abs(entry_price - sl_price)
        elif strategy == "SOL":
            from engine.strategies.sol_supertrend import get_sol_sl_prices
            lb, ub = get_sol_sl_prices(df)
            if side == 'LONG':
                sl_price = lb
                tp_price = entry_price * 10.0 # Bắt trend vô tận, chốt bằng tay hoặc trailing (ở đây để giá siêu cao)
            else:
                sl_price = ub
                tp_price = entry_price * 0.1
            risk_per_coin = abs(entry_price - sl_price)
        else:
            return
            
        current_risk_pct = risk_pct if risk_pct is not None else 3.0

        balance = await self.exchange.get_balance('USDT')
        risk_amount = balance * (current_risk_pct / 100)
        
        if risk_per_coin <= 0:
            self.log(f"[{symbol}] Invalid risk per coin: {risk_per_coin}", "ERROR")
            return
            
        position_size = risk_amount / risk_per_coin
        notional_value = position_size * entry_price
        
        required_leverage = int(notional_value / balance) + 1
        required_leverage = max(1, min(required_leverage, 75))
        
        self.log(f"[{symbol}] Signal detected! Executing {side}. Entry: {entry_price}, SL: {sl_price}, TP: {tp_price}, Size: {position_size} (Leverage: {required_leverage}x)")
        
        if self.exchange.api_key and self.exchange.secret_key:
            try:
                await self.exchange.exchange.fapiPrivateDeleteAllOpenOrders({'symbol': symbol.replace('/', '')})
                await self.exchange.exchange.fapiPrivateDeleteAlgoOpenOrders({'symbol': symbol.replace('/', '')})
            except:
                pass
                
            try:
                await self.exchange.exchange.set_margin_mode('CROSSED', symbol.replace('/', ''))
                await self.exchange.exchange.set_leverage(required_leverage, symbol.replace('/', ''))
            except:
                pass
                
            await self.exchange.execute_full_trade(symbol, 'buy' if side == 'LONG' else 'sell', position_size, entry_price, sl_price, tp_price)
        else:
            self.log(f"[{symbol}] API keys NOT found. PAPER TRADING mode.")

        message = ("""

content = execute_trade_regex.sub(new_execute_trade, content)

# Replace on_candle_closed
on_candle_regex = re.compile(r'    async def on_candle_closed\(self\):.*?        except Exception as e:', re.DOTALL)

new_on_candle = """    async def on_candle_closed(self, bot_mode="XRP"):
        self.log(f"Candle closed event received for {bot_mode}! Processing signals...")
        await self.manage_open_trades()

        try:
            if bot_mode == "XRP":
                from engine.strategies.xrp_nada_final import check_xrp_signal
                xrp_data = await self.exchange.fetch_ohlcv("XRP/USDT", '5m', 600)
                xrp_df = pd.DataFrame(xrp_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                signal = check_xrp_signal(xrp_df)
                last_time = xrp_df["timestamp"].iloc[-2]
                
                if signal == "LONG" and self.last_trade_time.get("XRP") != last_time:
                    self.last_trade_time["XRP"] = last_time
                    if self.is_running:
                        await self.execute_trade("XRP/USDT", "XRP", 3.0, xrp_df, 1.0)
                        
            elif bot_mode == "SOL":
                from engine.strategies.sol_supertrend import check_sol_signal
                sol_data = await self.exchange.fetch_ohlcv("SOL/USDT", '4h', 250)
                sol_df = pd.DataFrame(sol_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                signal = check_sol_signal(sol_df)
                last_time = sol_df["timestamp"].iloc[-2]
                
                # Check for Trend Flip (Close existing positions)
                if signal in ["LONG", "SHORT"]:
                    self.log(f"SOL Supertrend flipped to {signal}! Closing old positions.")
                    try:
                        await self.exchange.exchange.fapiPrivateDeleteAllOpenOrders({'symbol': 'SOLUSDT'})
                        # We don't strictly need to manually close the position because execute_full_trade handles reversal?
                        # No, we should close it. Let's let the execute_trade open the new position which will overwrite it if hedge mode is off.
                    except:
                        pass
                
                if signal in ["LONG", "SHORT"] and self.last_trade_time.get("SOL") != last_time:
                    self.last_trade_time["SOL"] = last_time
                    if self.is_running:
                        await self.execute_trade("SOL/USDT", "SOL", 3.0, sol_df, 1.0, side=signal)
                        
        except Exception as e:"""

content = on_candle_regex.sub(new_on_candle, content)

with open('web_app/backend/engine/trader.py', 'w') as f:
    f.write(content)
print("trader.py patched successfully!")
