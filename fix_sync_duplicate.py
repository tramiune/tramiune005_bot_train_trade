import re

with open("web_app/backend/engine/trader.py", "r") as f:
    content = f.read()

broken = """            last_trade = db.query(Trade).filter(Trade.strategy == "DOGE_3M_DEGEN").order_by(Trade.entry_time.desc()).first()
            last_trade_time = pd.to_datetime(last_trade.entry_time) if last_trade else pd.Timestamp('2000-01-01')
            
            added = 0"""

fixed = """            last_trade = db.query(Trade).filter(Trade.strategy == "DOGE_3M_DEGEN").order_by(Trade.entry_time.desc()).first()
            last_trade_time = pd.to_datetime(last_trade.entry_time) if last_trade else pd.Timestamp('2000-01-01')
            
            if last_trade and last_trade.status == "OPEN":
                self.log("Auto-Sync skipped: A trade is currently OPEN.")
                db.close()
                return
                
            added = 0"""

content = content.replace(broken, fixed)

with open("web_app/backend/engine/trader.py", "w") as f:
    f.write(content)
