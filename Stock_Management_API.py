# IFT 401 Proton Backend
# Stock_Management_API.py
# Toombs Theobald Tippeconnic

from fastapi import FastAPI, APIRouter, Depends, status, HTTPException
from Trading_Logic import app as trading_app
from Portfolio_Cash_Management import app as portfolio_app
from Transaction_History import app as transaction_app
from Market_Hours_Schedule import app as market_hours_app
from Middleware import app as middleware_app
from Logging_Error_Handling import app as logging_app
from Random_Stock_Price_Gen import update_stock_prices
from sqlalchemy.orm import Session, sessionmaker, declarative_base, relationship
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from database import get_db  
from auth_utils import get_admin_user, get_current_user  
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from typing import List

# FastAPI 
app = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/user/token")

# Database Config
DATABASE_URL = "postgresql://admindb:IFT401Project!@protondb.cz08cemoiob0.us-east-2.rds.amazonaws.com:5432/protondb"  
engine = create_engine(DATABASE_URL)  
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Stock Model
class Stock(Base):
    __tablename__ = "stocks"
    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String, nullable=False)
    ticker = Column(String, unique=True, nullable=False, index=True)
    volume = Column(Integer, nullable=False)
    initial_price = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    daily_high = Column(Float, nullable=False)  
    daily_low = Column(Float, nullable=False)   

Base.metadata.create_all(bind=engine)

# Pydantic Schemas
class StockCreate(BaseModel):
    company_name: str
    ticker: str
    volume: int
    initial_price: float

class StockUpdate(BaseModel):
    price: float

class StockResponse(BaseModel):
    company_name: str
    ticker: str
    volume: int
    initial_price: float
    price: float
    daily_high: float
    daily_low: float
    market_cap: float

    class Config:
        from_attributes = True

# Helper Function for Market Capitalization
def calculate_market_cap(stock: Stock) -> float:
    return stock.price * stock.volume

# Endpoints
@app.post("/create_stocks", response_model=StockResponse, status_code=status.HTTP_201_CREATED)
def create_new_stock(stock: StockCreate, db: Session = Depends(get_db), current_user=Depends(oauth2_scheme)):
    """
    Admin-only endpoint to create a new stock.
    """
    existing_stock = db.query(Stock).filter(Stock.ticker == stock.ticker).first()
    if existing_stock:
        raise HTTPException(status_code=400, detail="Stock with this ticker already exists")

    new_stock = Stock(
        company_name=stock.company_name,
        ticker=stock.ticker,
        volume=stock.volume,
        initial_price=stock.initial_price,
        price=stock.initial_price, 
        daily_high=stock.initial_price,
        daily_low=stock.initial_price, 
    )
    db.add(new_stock)
    db.commit()
    db.refresh(new_stock)
    return StockResponse(
        company_name=new_stock.company_name,
        ticker=new_stock.ticker,
        volume=new_stock.volume,
        initial_price=new_stock.initial_price,
        price=new_stock.price,
        daily_high=new_stock.daily_high,
        daily_low=new_stock.daily_low,
        market_cap=calculate_market_cap(new_stock),
    )

@app.get("/get_stocks", response_model=List[StockResponse])
def get_stocks(db: Session = Depends(get_db)):
    """
    Fetch a list of all available stocks with their daily high and low values.
    """
    stocks = db.query(Stock).all()
    return [
        StockResponse(
            company_name=stock.company_name,
            ticker=stock.ticker,
            volume=stock.volume,
            initial_price=stock.initial_price,
            price=stock.price,
            daily_high=stock.daily_high,
            daily_low=stock.daily_low,
            market_cap=calculate_market_cap(stock),
        )
        for stock in stocks
    ]

@app.patch("/name/{ticker}", response_model=StockResponse)
def update_stock_price(ticker: str, stock_update: StockUpdate, db: Session = Depends(get_db)):
    """
    Internal endpoint to update stock prices and track daily highs/lows.
    """
    stock = db.query(Stock).filter(Stock.ticker == ticker).first()
    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")

    new_price = stock_update.price

    # Update price
    stock.price = new_price

    # Adjust daily high/low 
    if new_price > stock.daily_high:
        stock.daily_high = new_price
    if new_price < stock.daily_low:
        stock.daily_low = new_price

    db.commit()
    db.refresh(stock)
    return StockResponse(
        company_name=stock.company_name,
        ticker=stock.ticker,
        volume=stock.volume,
        initial_price=stock.initial_price,
        price=stock.price,
        daily_high=stock.daily_high,
        daily_low=stock.daily_low,
        market_cap=calculate_market_cap(stock),
    )

# End
