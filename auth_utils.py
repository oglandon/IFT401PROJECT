# IFT 401 Proton Backend
# Auth_utils.py
# Toombs Theobald Tippeconnic

from fastapi import Depends, HTTPException, Query, Header
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from database import get_db  
from models import User  
from fastapi.security import OAuth2PasswordBearer
import os
from sqlalchemy import create_engine

SECRET_KEY = "your_secret_key"
ALGORITHM = "HS256"

# Database Config
DATABASE_URL = "postgresql://admindb:IFT401Project!@protondb.cz08cemoiob0.us-east-2.rds.amazonaws.com:5432/protondb"  
engine = create_engine(DATABASE_URL)  

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/user/token")

def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        user = db.query(User).filter(User.username == username).first()
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

def get_admin_user(current_user: User = Depends(get_current_user)):
    if current_user.role != "is_admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

# End