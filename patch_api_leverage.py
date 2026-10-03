import re

with open("web_app/backend/main.py", "r") as f:
    content = f.read()

old_api = """class SettingsUpdate(BaseModel):
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
    
    return {"status": "ok", "leverage_updated_on_binance": success}"""

new_api = """class SettingsUpdate(BaseModel):
    risk_pct: float

@app.get("/api/settings")
def get_settings(db: Session = Depends(get_db)):
    settings = db.query(Settings).first()
    if not settings:
        settings = Settings(risk_pct=30.0, leverage=20)
        db.add(settings)
        db.commit()
    return {"risk_pct": settings.risk_pct}

@app.post("/api/settings")
async def update_settings(data: SettingsUpdate, db: Session = Depends(get_db)):
    settings = db.query(Settings).first()
    if not settings:
        settings = Settings(risk_pct=data.risk_pct, leverage=20)
        db.add(settings)
    else:
        settings.risk_pct = data.risk_pct
        
    db.commit()
    return {"status": "ok"}"""

content = content.replace(old_api, new_api)

with open("web_app/backend/main.py", "w") as f:
    f.write(content)
