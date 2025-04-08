# IFT 401 Proton Backend
# Transaction_History.py
# Toombs Theobald Tippeconnic

from fastapi import FastAPI, HTTPException, Depends, Query, APIRouter
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
from typing import List
from datetime import datetime
from database import get_db

# FastAPI
app = APIRouter()

# Database Config
DATABASE_URL = "postgresql://admindb:IFT401Project!@protondb.cz08cemoiob0.us-east-2.rds.amazonaws.com:5432/protondb"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Create tables
Base.metadata.create_all(bind=engine)

# Models
class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    ticker = Column(String, nullable=True)
    quantity = Column(Integer, nullable=True)
    price = Column(Float, nullable=True)
    transaction_type = Column(String, nullable=False)  # buy, sell, deposit, withdrawal
    timestamp = Column(DateTime, default=datetime.utcnow)

# Pydantic Schemas
class TransactionItem(BaseModel):
    id: int
    user_id: int
    ticker: str | None
    quantity: int | None
    price: float | None
    transaction_type: str
    timestamp: datetime

    class Config:
        from_attributes = True

# Get all transactions in the system
@app.get("/all transactions", response_model=List[TransactionItem])
def get_all_transactions(db: Session = Depends(get_db)):
    transactions = db.query(Transaction).order_by(Transaction.timestamp.desc()).all()
    return [
        TransactionItem(
            id=txn.id,
            user_id=txn.user_id,
            ticker=txn.ticker,
            quantity=txn.quantity,
            price=txn.price,
            transaction_type=txn.transaction_type,
            timestamp=txn.timestamp,
        )
        for txn in transactions
    ]

# End
