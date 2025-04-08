# IFT 401 Proton Backend
# User_Auth.py
# Toombs Theobald Tippeconnic

from fastapi import FastAPI, HTTPException, Depends, status, APIRouter
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import BaseModel
from typing import Optional
from passlib.hash import bcrypt
from sqlalchemy import create_engine, Column, Integer, String, Boolean, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import os
from datetime import datetime, timedelta
from database import get_db  
from models import User  
from fastapi import APIRouter
from auth_utils import get_admin_user, get_current_user 

# Constants
SECRET_KEY = "your_secret_key_here"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# FastAPI 
app = APIRouter()
router = APIRouter()

# Database Configuration
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
    is_admin = Column(Boolean, default=False)
    cash_balance = Column(Float, default=10000.0)

Base.metadata.create_all(bind=engine)

# Pydantic Schemas
class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    is_admin: bool = False

class UserResponse(BaseModel):
    username: str
    email: str
    is_admin: bool

class Token(BaseModel):
    access_token: str
    token_type: str

# OAuth2 Config
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/user/token")

# Helper Functions
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_user(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()

def verify_password(plain_password: str, hashed_password: str):
    return bcrypt.verify(plain_password, hashed_password)

def authenticate_user(db: Session, username: str, password: str):
    user = get_user(db, username)
    if not user or not verify_password(password, user.hashed_password):
        return False
    return user

def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)) -> User:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")  # Correct to use user_id
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Fetch user by ID instead of username
        user = db.query(User).filter(User.id == user_id).first()
        
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        
        return user
    
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid credentials")

def get_admin_user(current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    return current_user

# Endpoints
@router.post("/register", response_model=UserResponse)
def register(user: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == user.username).first():
        raise HTTPException(status_code=400, detail="Username already exists")
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email already exists")
    hashed_password = bcrypt.hash(user.password)
    db_user = User(username=user.username, email=user.email, hashed_password=hashed_password, is_admin=user.is_admin)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return UserResponse(username=db_user.username, email=db_user.email, is_admin=db_user.is_admin)

@router.post("/token", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    # Use user.id instead of user.username
    access_token = create_access_token(data={"sub": str(user.id)})  
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserResponse)
def read_current_user(current_user: User = Depends(get_current_user)):
    return UserResponse(username=current_user.username, email=current_user.email, is_admin=current_user.is_admin)

@router.get("/admin-only")
def admin_only_route(current_user: User = Depends(get_admin_user)):
    return {"message": "Welcome, Admin!"}
