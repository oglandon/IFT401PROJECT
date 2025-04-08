# IFT 401 Proton Backend
# Random_Stock_Price_Gen.py
# Toombs Theobald Tippeconnic

import random
import threading
import time
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
    initial_price = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    daily_high = Column(Float, nullable=False)
    daily_low = Column(Float, nullable=False)

Base.metadata.create_all(bind=engine)

# Random Price Adjustment Function
def random_price_fluctuation(price: float) -> float:
    change_percent = random.uniform(-0.02, 0.02)  # Adjust ±2%
    new_price = price + (price * change_percent)
    return max(new_price, 0.01)

# Price Update Function
def update_stock_prices():
    db: Session = SessionLocal()
    try:
        stocks = db.query(Stock).all()
        for stock in stocks:
            original_price = stock.price
            new_price = random_price_fluctuation(stock.price)

            # Update high/low 
            if new_price > stock.daily_high:
                stock.daily_high = new_price
            if new_price < stock.daily_low:
                stock.daily_low = new_price

            stock.price = new_price

            print(f"[{datetime.utcnow()}] Updated {stock.ticker}: {original_price:.2f} -> {new_price:.2f} | High: {stock.daily_high:.2f}, Low: {stock.daily_low:.2f}")

        db.commit()
    except Exception as e:
        print(f"Error updating stock prices: {e}")
    finally:
        db.close()

# Flag to ensure updater starts only once
_updater_started = False

# Background Thread Starter
def start_price_updater(interval_seconds: int = 600):  # 600s = 10 minutes
    global _updater_started
    if _updater_started:
        return  # Already running

    def run():
        while True:
            update_stock_prices()
            time.sleep(interval_seconds)

    _updater_started = True
    threading.Thread(target=run, daemon=True).start()

# Public entry point
def initialize_stock_price_updater():
    start_price_updater()

# End
