# IFT 401 Proton Backend
# Logging_Error_Handling.py
# Toombs Theobald Tippeconnic

from fastapi import FastAPI, Request, HTTPException, APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime
import logging
from database import get_db  
from auth_utils import get_current_user  

# FastAPI 
app = APIRouter()

# Local Logging Config
LOG_FILE = f"backend_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Function to log messages locally
def log_event(message):
    """
    Logs messages locally instead of AWS CloudWatch.
    """
    logging.info(message)

# API route that logs user activity
@app.get("/portfolio")
def get_portfolio(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    log_event(f"User {current_user.username} accessed their portfolio.")
    return {"message": f"User {current_user.username}'s portfolio retrieved successfully"}

# End