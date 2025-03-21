# IFT 401 Proton Backend
# Transaction_History.py
# Toombs Theobald Tippeconnic

from fastapi import FastAPI, HTTPException, Depends, Query, APIRouter
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from datetime import datetime
from typing import List
from pydantic import BaseModel
from database import get_db  
from auth_utils import get_current_user  

# FastAPI 
app = APIRouter()

@app.get("/portfolio")
def get_portfolio(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return {"message": f"User {current_user.username}'s portfolio retrieved successfully"}

# Database Config
DATABASE_URL = "postgresql://admindb:IFT401Project!@protondb.cz08cemoiob0.us-east-2.rds.amazonaws.com:5432/protondb"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Models 
class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    ticker = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    transaction_type = Column(String, nullable=False)  # "buy" or "sell"
    timestamp = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

# Pydantic Schemas
class TransactionItem(BaseModel):
    id: int
    ticker: str
    quantity: int
    price: float
    transaction_type: str
    timestamp: datetime

class PaginatedTransactionsResponse(BaseModel):
    transactions: List[TransactionItem]
    total: int
    page: int
    size: int

# Endpoints
@app.get("/transactions", response_model=PaginatedTransactionsResponse)
def get_transaction_history(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Fetch paginated transaction history for the logged-in user.
    """
    query = db.query(Transaction).filter(Transaction.user_id == current_user.id)
    total = query.count()
    transactions = query.offset((page - 1) * size).limit(size).all()

    return PaginatedTransactionsResponse(
        transactions=[
            TransactionItem(
                id=txn.id,
                ticker=txn.ticker,
                quantity=txn.quantity,
                price=txn.price,
                transaction_type=txn.transaction_type,
                timestamp=txn.timestamp,
            )
            for txn in transactions
        ],
        total=total,
        page=page,
        size=size,
    )

# End

