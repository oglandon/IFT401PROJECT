# IFT 401 Proton Backend
# Trading_Logic.py
# Toombs Theobald Tippeconnic

from fastapi import FastAPI, HTTPException, Depends, status, APIRouter
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
from database import get_db  
from auth_utils import get_current_user 
from Market_Hours_Schedule import is_market_open
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from auth_utils import get_admin_user, get_current_user
from sqlalchemy import DateTime
from datetime import datetime
from Market_Hours_Schedule import validate_market_hours

# FastAPI 
app = APIRouter()

# Database Config
DATABASE_URL = "postgresql://admindb:IFT401Project!@protondb.cz08cemoiob0.us-east-2.rds.amazonaws.com:5432/protondb"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Secret and Algorithm
SECRET_KEY = "your_secret_key_here"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Define OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/user/token")

# Validate token and get current user
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")

        # Check that user_id is valid
        if user_id is None or not user_id.isdigit():
            raise HTTPException(status_code=401, detail="Invalid token payload")

        # Fetch user by ID
        user = db.query(User).filter(User.id == int(user_id)).one_or_none()

        if user is None:
            raise HTTPException(status_code=401, detail="User not found or invalid.")

        return user

    except JWTError as e:
        print(f"Token error: {e}")
        raise HTTPException(status_code=401, detail="Invalid or expired token")

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
class TradeRequest(BaseModel):
    ticker: str
    quantity: int

class TradeResponse(BaseModel):
    ticker: str
    quantity: int
    price: float
    transaction_type: str
    timestamp: datetime

class CancelOrderResponse(BaseModel):
    message: str

# Helper Functions
def validate_market_hours(db: Session):
    if not is_market_open():
        raise HTTPException(status_code=400, detail="Market is closed")

def get_stock(db: Session, ticker: str):
    stock = db.query(Stock).filter(Stock.ticker == ticker).first()
    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")
    return stock

def get_user_portfolio(db: Session, user_id: int, ticker: str):
    return db.query(Portfolio).filter(Portfolio.user_id == user_id, Portfolio.ticker == ticker).first()

# Endpoints
@app.post("/buy", response_model=TradeResponse)
def execute_buy_trade(trade_request: TradeRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Buy stocks: Deduct cash and add to portfolio.
    """
    validate_market_hours(db)
    stock = get_stock(db, trade_request.ticker)
    total_cost = stock.price * trade_request.quantity

    if current_user.cash_balance < total_cost:
        raise HTTPException(status_code=400, detail="Insufficient cash balance")

    current_user.cash_balance -= total_cost

    portfolio_entry = get_user_portfolio(db, current_user.id, trade_request.ticker)
    if portfolio_entry:
        portfolio_entry.quantity += trade_request.quantity
    else:
        new_portfolio_entry = Portfolio(user_id=current_user.id, ticker=trade_request.ticker, quantity=trade_request.quantity)
        db.add(new_portfolio_entry)

    transaction = Transaction(
        user_id=current_user.id,
        ticker=trade_request.ticker,
        quantity=trade_request.quantity,
        price=stock.price,
        transaction_type="buy"
    )
    db.add(transaction)
    db.commit()

    return TradeResponse(
        ticker=trade_request.ticker,
        quantity=trade_request.quantity,
        price=stock.price,
        transaction_type="buy",
        timestamp=transaction.timestamp
    )

@app.post("/sell", response_model=TradeResponse)
def sell_stock(trade_request: TradeRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Sell stocks: Remove from portfolio and credit cash.
    """
    validate_market_hours(db)
    stock = get_stock(db, trade_request.ticker)

    portfolio_entry = get_user_portfolio(db, current_user.id, trade_request.ticker)
    if not portfolio_entry or portfolio_entry.quantity < trade_request.quantity:
        raise HTTPException(status_code=400, detail="Not enough stocks in portfolio to sell")

    total_revenue = stock.price * trade_request.quantity
    current_user.cash_balance += total_revenue

    portfolio_entry.quantity -= trade_request.quantity
    if portfolio_entry.quantity == 0:
        db.delete(portfolio_entry)

    transaction = Transaction(
        user_id=current_user.id,
        ticker=trade_request.ticker,
        quantity=-trade_request.quantity,
        price=stock.price,
        transaction_type="sell"
    )
    db.add(transaction)
    db.commit()

    return TradeResponse(
        ticker=trade_request.ticker,
        quantity=trade_request.quantity,
        price=stock.price,
        transaction_type="sell",
        timestamp=transaction.timestamp
    )

@app.delete("/order/{order_id}", response_model=CancelOrderResponse)
def cancel_order(order_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Cancel orders: Simulated order cancellation (not in real-time trading).
    """
    transaction = db.query(Transaction).filter(Transaction.id == order_id, Transaction.user_id == current_user.id).first()
    if not transaction:
        raise HTTPException(status_code=404, detail="Order not found or not eligible for cancellation")

    db.delete(transaction)
    db.commit()
    return CancelOrderResponse(message="Order successfully cancelled")

# End