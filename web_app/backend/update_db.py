from database import engine, SessionLocal
from models import Base, Settings

Base.metadata.create_all(bind=engine)

db = SessionLocal()
if not db.query(Settings).first():
    db.add(Settings(risk_pct=30.0, leverage=20))
    db.commit()
db.close()
print("DB migration done!")
