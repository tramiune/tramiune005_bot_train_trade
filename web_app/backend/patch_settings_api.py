import re

with open("web_app/backend/main.py", "r") as f:
    content = f.read()

settings_api = """
from pydantic import BaseModel
class SettingsUpdate(BaseModel):
    risk_pct: float

@app.get("/api/settings")
def get_settings(db: Session = Depends(get_db)):
    settings = db.query(Settings).first()
    if not settings:
        settings = Settings(risk_pct=30.0)
        db.add(settings)
        db.commit()
    return {"risk_pct": settings.risk_pct}

@app.post("/api/settings")
def update_settings(data: SettingsUpdate, db: Session = Depends(get_db)):
    settings = db.query(Settings).first()
    if not settings:
        settings = Settings(risk_pct=data.risk_pct)
        db.add(settings)
    else:
        settings.risk_pct = data.risk_pct
    db.commit()
    return {"status": "ok"}
"""

# Insert before the first @app.get
content = content.replace("@app.get(\"/api/status\")", settings_api + "\n@app.get(\"/api/status\")")

with open("web_app/backend/main.py", "w") as f:
    f.write(content)
print("Settings API patched!")
