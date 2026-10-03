with open("web_app/backend/engine/trader.py", "r") as f:
    content = f.read()

import re
old_sync = re.search(r'    async def sync_missed_trades\(self\):.*?finally:\n            db\.close\(\)', content, flags=re.DOTALL)

new_sync = """    async def sync_missed_trades(self):
        self.log("Syncing missed trades for DOGE_3M_DEGEN...")
        try:
            from kline_cache import KLINES_CACHE
            cache_key = "DOGEUSDT_3m"
            if cache_key not in KLINES_CACHE:
                return
                
            import pandas as pd
            df = pd.DataFrame(KLINES_CACHE[cache_key])
            df = df.rename(columns={'time': 'timestamp'})
            df['timestamp'] = df['timestamp'] * 1000
            
            from engine.backtester import backtest_doge_3m_degen
            missed_trades = backtest_doge_3m_degen(df)
            
            db = SessionLocal()
            last_trade = db.query(Trade).filter(Trade.strategy == "DOGE_3M_DEGEN").order_by(Trade.entry_time.desc()).first()
            last_trade_time = last_trade.entry_time.timestamp() if last_trade and last_trade.entry_time else 0
            
            if last_trade and last_trade.status == "OPEN":
                self.log("Auto-Sync skipped: A trade is currently OPEN.")
                db.close()
                return
                
            added = 0
            from datetime import datetime
            for t in missed_trades:
                if t['time'] <= last_trade_time:
                    continue
                    
                trade = Trade(
                    symbol="DOGE/USDT",
                    strategy="DOGE_3M_DEGEN",
                    side=t['side'],
                    entry_price=t['entry'],
                    stop_loss=t['sl'],
                    take_profit=t['tp'],
                    exit_price=t['exit_price'],
                    pnl=t['pnl'],
                    status="CLOSED",
                    entry_time=datetime.fromtimestamp(t['time']),
                    exit_time=datetime.fromtimestamp(t['exit_time'])
                )
                db.add(trade)
                added += 1
                
            if added > 0:
                db.commit()
                self.log(f"Auto-Sync complete! Recovered {added} missed closed trades.")
            else:
                self.log("Auto-Sync complete. No missed trades found.")
                
        except Exception as e:
            self.log(f"Auto-Sync error: {e}", "ERROR")
        finally:
            db.close()"""

if old_sync:
    content = content.replace(old_sync.group(0), new_sync)
    with open("web_app/backend/engine/trader.py", "w") as f:
        f.write(content)
    print("Patched successfully!")
else:
    print("Could not find sync_missed_trades")
