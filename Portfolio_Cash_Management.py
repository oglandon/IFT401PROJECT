# IFT 401 Proton Backend
# Portfolio_Cash_Management.py
# Toombs Theobald Tippeconnic

from fastapi import FastAPI, HTTPException, Depends, status, APIRouter
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from pydantic import BaseModel
from typing import List
from database import get_db  
from auth_utils import get_current_user  

# FastAPI 
app = APIRouter()

@app.get("/portfolio", operation_id="retrieve_portfolio_data_unique")
def retrieve_portfolio_data(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return {"message": f"User {current_user.username}'s portfolio retrieved successfully"}

# Database Config
DATABASE_URL = "postgresql://admindb:IFT401Project!@protondb.cz08cemoiob0.us-east-2.rds.amazonaws.com:5432/protondb"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Models 
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    cash_balance = Column(Float, default=10000.0)  # Default starting cash

class Stock(Base):
    __tablename__ = "stocks"
    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String, nullable=False)
    ticker = Column(String, unique=True, nullable=False, index=True)
    volume = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)

class Portfolio(Base):
    __tablename__ = "portfolio"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    ticker = Column(String, ForeignKey("stocks.ticker"), nullable=False)
    quantity = Column(Integer, nullable=False)
    user = relationship("User", back_populates="portfolio")

User.portfolio = relationship("Portfolio", back_populates="user")

Base.metadata.create_all(bind=engine)

# Pydantic Schemas
class PortfolioItem(BaseModel):
    ticker: str
    quantity: int
    value: float

class PortfolioResponse(BaseModel):
    cash_balance: float
    stocks: List[PortfolioItem]

class CashTransactionRequest(BaseModel):
    amount: float

class CashTransactionResponse(BaseModel):
    message: str
    cash_balance: float

# Endpoints
@app.get("/portfolio", response_model=PortfolioResponse)
def retrieve_portfolio_data(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    View Portfolio: Fetch user's owned stocks with quantities and values.
    """
    portfolio_entries = db.query(Portfolio).filter(Portfolio.user_id == current_user.id).all()
    stocks = []

    for entry in portfolio_entries:
        stock = db.query(Stock).filter(Stock.ticker == entry.ticker).first()
        if stock:
            stocks.append(
                PortfolioItem(
                    ticker=entry.ticker,
                    quantity=entry.quantity,
                    value=entry.quantity * stock.price,
                )
            )

    return PortfolioResponse(cash_balance=current_user.cash_balance, stocks=stocks)

@app.post("/cash/deposit", response_model=CashTransactionResponse)
def deposit_cash(transaction: CashTransactionRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Deposit Cash: Add funds to the user's cash account.
    """
    if transaction.amount <= 0:
        raise HTTPException(status_code=400, detail="Deposit amount must be greater than zero")

    current_user.cash_balance += transaction.amount
    db.commit()
    return CashTransactionResponse(
        message="Cash deposited successfully",
        cash_balance=current_user.cash_balance,
    )

@app.post("/cash/withdraw", response_model=CashTransactionResponse)
def withdraw_cash(transaction: CashTransactionRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Withdraw Cash: Remove funds from the user's cash account.
    """
    if transaction.amount <= 0:
        raise HTTPException(status_code=400, detail="Withdrawal amount must be greater than zero")
    if current_user.cash_balance < transaction.amount:
        raise HTTPException(status_code=400, detail="Insufficient funds in cash account")

    current_user.cash_balance -= transaction.amount
    db.commit()
    return CashTransactionResponse(
        message="Cash withdrawn successfully",
        cash_balance=current_user.cash_balance,
    )

# End