with open("main.py", "r") as f:
    content = f.read()

settings_api = """
from pydantic import BaseModel
class SettingsUpdate(BaseModel):
    risk_pct: float
    leverage: int

@app.get("/api/settings")
def get_settings(db: Session = Depends(get_db)):
    settings = db.query(Settings).first()
    if not settings:
        settings = Settings(risk_pct=30.0, leverage=20)
        db.add(settings)
        db.commit()
    return {"risk_pct": settings.risk_pct, "leverage": settings.leverage}

@app.post("/api/settings")
async def update_settings(data: SettingsUpdate, db: Session = Depends(get_db)):
    settings = db.query(Settings).first()
    if not settings:
        settings = Settings(risk_pct=data.risk_pct, leverage=data.leverage)
        db.add(settings)
    else:
        settings.risk_pct = data.risk_pct
        settings.leverage = data.leverage
        
    db.commit()
    
    # Try setting leverage on Binance if API keys exist
    from engine.exchange import BinanceFutures
    exchange = BinanceFutures()
    success = await exchange.set_leverage("DOGEUSDT", data.leverage)
    await exchange.close()
    
    return {"status": "ok", "leverage_updated_on_binance": success}
"""

if "@app.get(\"/api/settings\")" not in content:
    content = content.replace("app = FastAPI()", "app = FastAPI()\n" + settings_api)

with open("main.py", "w") as f:
    f.write(content)
