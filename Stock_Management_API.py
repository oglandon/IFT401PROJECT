# IFT 401 Proton Backend
# Stock_Management_API.py
# Toombs Theobald Tippeconnic

from fastapi import FastAPI
from Trading_Logic import app as trading_app
from Portfolio_Cash_Management import app as portfolio_app
from Transaction_History import app as transaction_app
from Market_Hours_Schedule import app as market_hours_app
from Middleware import app as middleware_app
from Logging_Error_Handling import app as logging_app
from Random_Stock_Price_Gen import update_stock_prices
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy import create_engine  
from database import get_db  
from auth_utils import get_admin_user, get_current_user  
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from pydantic import BaseModel
from typing import List

# FastAPI 
app = APIRouter()

@app.post("/stocks", operation_id="create_stock_entry")
def create_new_stock(stock_data: dict, db: Session = Depends(get_db), current_user=Depends(get_admin_user)):
    # Stock creation logic
    return {"message": "Stock created successfully"}

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
    market_cap: float

    class Config:
        orm_mode = True

# Helper Function for Market Capitalization
def calculate_market_cap(stock: Stock) -> float:
    return stock.price * stock.volume

# Endpoints
@app.post("/stocks", response_model=StockResponse, status_code=status.HTTP_201_CREATED)
def create_new_stock(stock: StockCreate, db: Session = Depends(get_db), current_user=Depends(get_admin_user)):
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
        price=stock.initial_price,  # Initial price is the same as current price
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
        market_cap=calculate_market_cap(new_stock),
    )

@app.get("/stocks", response_model=List[StockResponse])
def get_stocks(db: Session = Depends(get_db)):
    """
    Fetch a list of all available stocks.
    """
    stocks = db.query(Stock).all()
    return [
        StockResponse(
            company_name=stock.company_name,
            ticker=stock.ticker,
            volume=stock.volume,
            initial_price=stock.initial_price,
            price=stock.price,
            market_cap=calculate_market_cap(stock),
        )
        for stock in stocks
    ]

@app.patch("/stocks/{ticker}", response_model=StockResponse)
def update_stock_price(ticker: str, stock_update: StockUpdate, db: Session = Depends(get_db)):
    """
    Internal endpoint to update stock prices.
    """
    stock = db.query(Stock).filter(Stock.ticker == ticker).first()
    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")

    stock.price = stock_update.price
    db.commit()
    db.refresh(stock)
    return StockResponse(
        company_name=stock.company_name,
        ticker=stock.ticker,
        volume=stock.volume,
        initial_price=stock.initial_price,
        price=stock.price,
        market_cap=calculate_market_cap(stock),
    )

# End