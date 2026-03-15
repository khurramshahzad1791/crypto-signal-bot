from sqlalchemy import create_engine, Column, String, Float, DateTime, Integer, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

Base = declarative_base()

class Trade(Base):
    __tablename__ = 'trades'
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    pair = Column(String)
    signal_type = Column(String)
    entry_price = Column(Float)
    exit_price = Column(Float, nullable=True)
    stop_loss = Column(Float)
    take_profit = Column(Float)
    outcome = Column(String, nullable=True)  # 'win', 'loss', 'open'
    pnl_percent = Column(Float, nullable=True)
    confidence = Column(Integer)

class SignalLog(Base):
    __tablename__ = 'signal_logs'
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    pair = Column(String)
    signal_type = Column(String)
    price = Column(Float)
    confidence = Column(Integer)

# Ensure data directory exists
os.makedirs("/app/data", exist_ok=True)
engine = create_engine('sqlite:////app/data/trades.db', echo=False)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
