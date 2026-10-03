import re

with open("web_app/backend/engine/trader.py", "r") as f:
    content = f.read()

# Modify execute_trade signature to fetch from Settings if not passed
old_exec = "    async def execute_trade(self, df: pd.DataFrame, signal: str, symbol: str, risk_pct: float = 2.0, strategy: str = 'DEGEN'):"
new_exec = "    async def execute_trade(self, df: pd.DataFrame, signal: str, symbol: str, risk_pct: float = None, strategy: str = 'DEGEN'):"
content = content.replace(old_exec, new_exec)

# Inside execute_trade, fetch risk_pct
old_risk = """        # Calculate size based on risk
        balance = await self.exchange.get_balance('USDT')
        risk_amount = balance * (risk_pct / 100)"""

new_risk = """        # Fetch Settings from DB
        from models import Settings
        from database import SessionLocal
        db = SessionLocal()
        settings = db.query(Settings).first()
        db.close()
        
        current_risk_pct = risk_pct if risk_pct is not None else (settings.risk_pct if settings else 30.0)

        # Calculate size based on risk
        balance = await self.exchange.get_balance('USDT')
        risk_amount = balance * (current_risk_pct / 100)"""
        
content = content.replace(old_risk, new_risk)

with open("web_app/backend/engine/trader.py", "w") as f:
    f.write(content)
