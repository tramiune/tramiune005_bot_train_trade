from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime
from datetime import datetime, timezone
from database import Base

class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    strategy = Column(String)
    side = Column(String) # 'LONG' or 'SHORT'
    entry_price = Column(Float)
    exit_price = Column(Float, nullable=True)
    stop_loss = Column(Float)
    take_profit = Column(Float, nullable=True)
    size = Column(Float)
    pnl = Column(Float, nullable=True)
    status = Column(String) # 'OPEN', 'CLOSED', 'CANCELED'
    entry_time = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    exit_time = Column(DateTime, nullable=True)
    
class BotConfig(Base):
    __tablename__ = "bot_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    strategy = Column(String, unique=True, index=True)
    is_active = Column(Boolean, default=False)
    risk_per_trade_pct = Column(Float, default=3.0)
    
class SystemLog(Base):
    __tablename__ = "system_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    level = Column(String) # INFO, WARNING, ERROR
    message = Column(String)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
