import re

with open("web_app/backend/engine/trader.py", "r") as f:
    content = f.read()

rule_logic = """                # 2.5 DOGE 3m Degen
                if "DOGE_3M_DEGEN" in active_strategies:
                    # Check if there's already an open trade
                    db = SessionLocal()
                    has_open = db.query(Trade).filter(Trade.strategy == "DOGE_3M_DEGEN", Trade.status == "OPEN").first()
                    db.close()
                    
                    if not has_open:
                        doge_3m_data = await self.exchange.fetch_ohlcv("DOGE/USDT", '3m', 250)
                        doge_3m_df = pd.DataFrame(doge_3m_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                        signal = check_doge_degen_signal(doge_3m_df)
                        last_time = doge_3m_df["timestamp"].iloc[-2]
                        
                        if signal and self.last_trade_time.get("DOGE_3M_DEGEN") != last_time:
                            self.last_trade_time["DOGE_3M_DEGEN"] = last_time
                            conf = next(c for c in configs if c.strategy == "DOGE_3M_DEGEN")
                            await self.execute_trade("DOGE/USDT", "DOGE_3M_DEGEN", conf.risk_per_trade_pct, doge_3m_df, 1.0, side=signal)"""

old_logic = """                # 2.5 DOGE 3m Degen
                if "DOGE_3M_DEGEN" in active_strategies:
                    doge_3m_data = await self.exchange.fetch_ohlcv("DOGE/USDT", '3m', 250)
                    doge_3m_df = pd.DataFrame(doge_3m_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                    signal = check_doge_degen_signal(doge_3m_df)
                    last_time = doge_3m_df["timestamp"].iloc[-2]
                    
                    if signal and self.last_trade_time.get("DOGE_3M_DEGEN") != last_time:
                        self.last_trade_time["DOGE_3M_DEGEN"] = last_time
                        conf = next(c for c in configs if c.strategy == "DOGE_3M_DEGEN")
                        # execute_trade modifies SL/TP based on old logic, we must override it for DOGE_3M_DEGEN!
                        # Let's bypass execute_trade or just let execute_trade know.
                        await self.execute_trade("DOGE/USDT", "DOGE_3M_DEGEN", conf.risk_per_trade_pct, doge_3m_df, 1.0, side=signal)"""

content = content.replace(old_logic, rule_logic)

with open("web_app/backend/engine/trader.py", "w") as f:
    f.write(content)
