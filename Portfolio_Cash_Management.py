# IFT 401 Proton Backend
# Portfolio_Cash_Management.py
# Toombs Theobald Tippeconnic

from fastapi import FastAPI, HTTPException, Depends, status, APIRouter
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from pydantic import BaseModel
from typing import List
from database import get_db
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from auth_utils import get_admin_user, get_current_user
from sqlalchemy import DateTime
from datetime import datetime
from typing import Optional


# FastAPI App
app = APIRouter()

# Secret and Algorithm
SECRET_KEY = "your_secret_key_here"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Define OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/user/token")

# Create engine and Base
DATABASE_URL = "postgresql://admindb:IFT401Project!@protondb.cz08cemoiob0.us-east-2.rds.amazonaws.com:5432/protondb"
engine = create_engine(DATABASE_URL)
Base = declarative_base()

# Create tables
Base.metadata.create_all(bind=engine)


# Models
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    cash_balance = Column(Float, default=10000.0)
    is_admin = Column(Boolean, default=False)

    # Define relationship for transactions
    transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")


class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    ticker = Column(String(10), nullable=True, default=None)
    quantity = Column(Integer, nullable=True, default=None)
    price = Column(Float, nullable=True, default=None)
    type = Column(String(10), nullable=True, default=None)
    timestamp = Column(DateTime, default=datetime.utcnow)
    amount = Column(Float, nullable=True)
    transaction_type = Column(String(20), nullable=True)
    
    # Correct relationship for user
    user = relationship("User", back_populates="transactions")


# Pydantic Schemas
class TransactionCreate(BaseModel):
    amount: float


class TransactionResponse(BaseModel):
    id: int
    user_id: int
    amount: Optional[float]
    transaction_type: str

    class Config:
        from_attributes = True


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


# Endpoints
@app.post("/deposit", response_model=TransactionResponse, status_code=status.HTTP_200_OK)
def deposit_funds(
    transaction: TransactionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Deposit funds to the user’s portfolio
    if transaction.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive.")

    # Update user's balance
    current_user.cash_balance += transaction.amount

    # Create a new transaction for deposit
    new_transaction = Transaction(
        user_id=current_user.id,
        ticker=None,              # Set NULL values for deposit
        quantity=None,            # Set NULL values for deposit
        price=None,               # Set NULL values for deposit
        type=None,                # Set NULL values for deposit
        amount=transaction.amount,
        transaction_type="deposit",
        timestamp=datetime.utcnow(),
    )

    # Add and commit to the database
    db.add(new_transaction)
    db.commit()
    db.refresh(new_transaction)

    # Return the transaction response
    return TransactionResponse(
        id=new_transaction.id,
        user_id=new_transaction.user_id,
        amount=new_transaction.amount,
        transaction_type=new_transaction.transaction_type,
    )


@app.post("/withdraw", response_model=TransactionResponse, status_code=status.HTTP_200_OK)
def withdraw_funds(
    transaction: TransactionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)  
):
    # Withdraw funds from the user’s portfolio
    if transaction.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive.")
    if current_user.cash_balance < transaction.amount:
        raise HTTPException(status_code=400, detail="Insufficient balance.")

    current_user.cash_balance -= transaction.amount
    new_transaction = Transaction(
        user_id=current_user.id, amount=transaction.amount, transaction_type="withdrawal"
    )
    db.add(new_transaction)
    db.commit()
    db.refresh(new_transaction)

    return TransactionResponse(
        id=new_transaction.id,
        user_id=new_transaction.user_id,
        amount=new_transaction.amount,
        transaction_type=new_transaction.transaction_type,
    )


@app.get("/transactions", response_model=List[TransactionResponse])
def get_transactions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Get all transactions of the current user
    transactions = db.query(Transaction).filter(Transaction.user_id == current_user.id).all()
    return [
        TransactionResponse(
            id=transaction.id,
            user_id=transaction.user_id,
            amount=transaction.amount,
            transaction_type=transaction.transaction_type,
        )
        for transaction in transactions
    ]


@app.get("/balance")
def get_balance(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Return the current user's balance
    return {"username": current_user.username, "cash_balance": current_user.cash_balance}



@app.get("/owned_stocks")
def get_owned_stocks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Return the user's currently owned stock tickers and quantities.
    """
    # Aggregate owned stocks by user
    owned_stocks = (
        db.query(Transaction.ticker, Transaction.quantity)
        .filter(
            Transaction.user_id == current_user.id,
            Transaction.transaction_type.in_(["buy", "sell"]),
            Transaction.ticker.isnot(None)
        )
        .all()
    )

    if not owned_stocks:
        return {"username": current_user.username, "owned_stocks": []}

    # Calculate net quantities
    stock_holdings = {}
    for ticker, qty in owned_stocks:
        if ticker not in stock_holdings:
            stock_holdings[ticker] = 0
        stock_holdings[ticker] += qty

    # Remove stocks with zero or negative holdings
    net_stocks = {ticker: qty for ticker, qty in stock_holdings.items() if qty > 0}

    return {
        "username": current_user.username,
        "owned_stocks": [{"ticker": ticker, "quantity": qty} for ticker, qty in net_stocks.items()]
    }



# End