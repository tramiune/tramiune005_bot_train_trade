with open("models.py", "r") as f:
    content = f.read()

if "class Settings(Base):" not in content:
    content += """
class Settings(Base):
    __tablename__ = "settings"
    id = Column(Integer, primary_key=True, index=True)
    risk_pct = Column(Float, default=2.0)
    leverage = Column(Integer, default=20)
"""
    with open("models.py", "w") as f:
        f.write(content)
