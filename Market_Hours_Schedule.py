# IFT 401 Proton Backend
# Market_Hours_Schedule.py
# Toombs Theobald Tippeconnic

from fastapi import FastAPI, HTTPException, Depends, status, APIRouter
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, time, timedelta
from database import get_db  
from auth_utils import get_current_user, get_admin_user  
from fastapi.security import OAuth2PasswordBearer

# FastAPI 
app = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/user/token")

# Database Config
DATABASE_URL = "postgresql://admindb:IFT401Project!@protondb.cz08cemoiob0.us-east-2.rds.amazonaws.com:5432/protondb"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Models
class MarketSchedule(Base):
    __tablename__ = "market_schedule"
    id = Column(Integer, primary_key=True, index=True)
    day_of_week = Column(Integer, nullable=False)  # 0 = Monday, 6 = Sunday
    is_open = Column(Boolean, default=True)       # Whether the market is open
    opening_time = Column(String, default="00:01")  # Opening time (24-hour format)
    closing_time = Column(String, default="23:59")  # Closing time (24-hour format)

Base.metadata.create_all(bind=engine)

# Pydantic Schemas
class MarketHours(BaseModel):
    day_of_week: int
    is_open: bool
    opening_time: str
    closing_time: str

    class Config:
        orm_mode = True

class UpdateMarketHoursRequest(BaseModel):
    day_of_week: int
    is_open: Optional[bool] = None
    opening_time: Optional[str] = None
    closing_time: Optional[str] = None

class MarketHoursResponse(BaseModel):
    schedule: list[MarketHours]

# Helper Functions
def validate_market_hours(db: Session):
    """
    Function to ensure the current time is within market hours.
    """
    now = datetime.utcnow()
    current_day = now.weekday()
    current_time = now.time()

    schedule = db.query(MarketSchedule).filter(MarketSchedule.day_of_week == current_day).first()
    if not schedule or not schedule.is_open:
        raise HTTPException(status_code=400, detail="Market is currently closed")

    opening_time = time.fromisoformat(schedule.opening_time)
    closing_time = time.fromisoformat(schedule.closing_time)

    if not (opening_time <= current_time <= closing_time):
        raise HTTPException(status_code=400, detail="Market is currently closed")


# Is market open function
def is_market_open():
    now = datetime.utcnow()
    # Market opens Mon-Fri from 9:30 AM - 10:00 PM UTC
    opening_time = now.replace(hour=0, minute=0, second=0, microsecond=1)
    closing_time = now.replace(hour=23, minute=0, second=5, microsecond=9)

    if now.weekday() >= 7:  # Saturday(5) & Sunday(6)
        return False
    return opening_time <= now <= closing_time

def seed_market_hours(db: Session):
    """
    Seed initial market hours for all days of the week if not already populated.
    """
    existing_schedule = db.query(MarketSchedule).count()
    if existing_schedule == 0:
        default_schedule = [
            MarketSchedule(day_of_week=i, is_open=True, opening_time="00:01", closing_time="23:59")
            for i in range(7)  # 0 = Monday, 6 = Sunday
        ]
        db.bulk_save_objects(default_schedule)
        db.commit()

# Endpoints
@app.get("/market/hours", response_model=MarketHoursResponse)
def fetch_market_hours(db: Session = Depends(get_db)):
    """
    Fetch the current market hours schedule.
    """
    schedule = db.query(MarketSchedule).all()

    # Map MarketSchedule (SQLAlchemy Model) -> MarketHours (Pydantic Model)
    schedule_data = [
        MarketHours(
            day_of_week=schedule_item.day_of_week,
            is_open=schedule_item.is_open,
            opening_time=schedule_item.opening_time,
            closing_time=schedule_item.closing_time,
        )
        for schedule_item in schedule
    ]
    
    return MarketHoursResponse(schedule=schedule_data)

@app.on_event("startup")
def startup_event():
    db = SessionLocal()
    seed_market_hours(db)
    db.close()

@app.patch("/market/hours", response_model=MarketHoursResponse)
def update_market_hours(
    request: UpdateMarketHoursRequest,
    db: Session = Depends(get_db),
    current_user = Depends(oauth2_scheme)
):
    """
    Admin-only endpoint to update market hours or holiday schedules.
    """
    schedule = db.query(MarketSchedule).filter(MarketSchedule.day_of_week == request.day_of_week).first()
    
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule for this day not found")

    # Update only the fields provided in the request
    if request.is_open is not None:
        schedule.is_open = request.is_open
    if request.opening_time:
        schedule.opening_time = request.opening_time
    if request.closing_time:
        schedule.closing_time = request.closing_time

    # Commit the updates
    db.commit()
    db.refresh(schedule)

    # Fetch the updated schedule after commit
    updated_schedule = db.query(MarketSchedule).all()

    # Map updated SQLAlchemy objects to Pydantic models
    schedule_data = [
        MarketHours(
            day_of_week=schedule_item.day_of_week,
            is_open=schedule_item.is_open,
            opening_time=schedule_item.opening_time,
            closing_time=schedule_item.closing_time,
        )
        for schedule_item in updated_schedule
    ]

    return MarketHoursResponse(schedule=schedule_data)

# End

