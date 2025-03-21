# IFT 401 Proton Backend
# Random_Stock_Price_Gen.py
# Toombs Theobald Tippeconnic

import random
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime

# Database Config
DATABASE_URL = "postgresql://admindb:IFT401Project!@protondb.cz08cemoiob0.us-east-2.rds.amazonaws.com:5432/protondb"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Models
class Stock(Base):
    __tablename__ = "stocks"
    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String, nullable=False)
    ticker = Column(String, unique=True, nullable=False, index=True)
    volume = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)

Base.metadata.create_all(bind=engine)

# Random Price Adjustment Function
def random_price_fluctuation(price: float) -> float:
    """
    Apply a random walk adjustment to the stock price.
    Ensures the price does not drop below 0.01.
    """
    change_percent = random.uniform(-0.02, 0.02)  # Adjust price by +/- 2%
    new_price = price + (price * change_percent)
    return max(new_price, 0.01)  # Ensure price stays above a minimum 

# Price Update Function
def update_stock_prices():
    """
    Update the stock prices in the database using a random walk algorithm.
    """
    db: Session = SessionLocal()
    try:
        stocks = db.query(Stock).all()
        for stock in stocks:
            original_price = stock.price
            stock.price = random_price_fluctuation(stock.price)
            print(f"Updated {stock.ticker}: {original_price:.2f} -> {stock.price:.2f}")
        db.commit()
    except Exception as e:
        print(f"Error updating stock prices: {e}")
    finally:
        db.close()

# End
