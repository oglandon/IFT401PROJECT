# IFT 401 Proton Backend
# Middleware.py
# Toombs Theobald Tippeconnic

from fastapi import FastAPI, HTTPException, Request, Depends, APIRouter
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from datetime import datetime, time
from typing import Optional
from database import get_db  
from auth_utils import get_current_user  
from models import User  
from Trading_Logic import execute_buy_trade

# FastAPI 
app = APIRouter()

# OAuth2 config
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Middleware Functions
def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)) -> User:
    """
    Middleware to validate JWT tokens and fetch the current user.
    """
    try:
        payload = jwt.decode(token, "your_secret_key", algorithms=["HS256"])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        user = db.query(User).filter(User.username == username).first()
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

def check_admin(current_user: User = Depends(get_current_user)):
    """
    Middleware to enforce admin-only access.
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

def validate_market_hours(db: Session = Depends(get_db)):
    """
    Middleware to check if the market is open.
    """
    now = datetime.utcnow()
    current_day = now.weekday()  # 0 = Monday, 6 = Sunday
    current_time = now.time()

    schedule = db.query(MarketSchedule).filter(MarketSchedule.day == current_day).first()
    if not schedule or not schedule.is_open:
        raise HTTPException(status_code=400, detail="Market is currently closed")

    opening_time = time.fromisoformat(schedule.opening_time)
    closing_time = time.fromisoformat(schedule.closing_time)

    if not (opening_time <= current_time <= closing_time):
        raise HTTPException(status_code=400, detail="Market is currently closed")

# Endpoints with Middleware

@app.get("/users/me")
def get_user_profile(current_user: User = Depends(get_current_user)):
    """
    Protected endpoint to fetch user profile using authentication middleware.
    """
    return {"username": current_user.username, "role": current_user.role, "cash_balance": current_user.cash_balance}

@app.get("/admin/dashboard")
def admin_dashboard(current_user: User = Depends(check_admin)):
    """
    Admin-only endpoint to access dashboard.
    """
    return {"message": "Welcome to the admin dashboard!"}

@app.post("/trade/buy")
def buy_stock(
    ticker: str,
    quantity: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(validate_market_hours),
):
    """
    Trade endpoint with market validation.
    """
    trade_result = buy_stock(ticker="AAPL", quantity=10, db=db, current_user=current_user)
    return {"message": f"Successfully bought {quantity} shares of {ticker}"}

# End

