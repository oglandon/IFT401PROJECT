# IFT 401 Proton Backend
# Loggin_Error_Handing_AWS.py
# Toombs Theobald Tippeconnic

from fastapi import FastAPI, Request, HTTPException, APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime
import boto3
from botocore.exceptions import NoCredentialsError
from Trading_Logic import execute_buy_trade, deposit_funds

# Import dependencies before using them
from database import get_db  
from auth_utils import get_current_user  

# FastAPI 
app = APIRouter()

@app.get("/portfolio")
def get_portfolio(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return {"message": f"User {current_user.username}'s portfolio retrieved successfully"}

# AWS CloudWatch Config
AWS_REGION = "us-east-2"
LOG_GROUP = "StockTradingAppLogs"
LOG_STREAM = f"backend-log-stream-{datetime.utcnow().strftime('%Y%m%d')}"

# Set up CloudWatch Logs
client = boto3.client("logs", region_name=AWS_REGION)
try:
    # Ensure the log group exists
    client.create_log_group(logGroupName=LOG_GROUP)
except client.exceptions.ResourceAlreadyExistsException:
    pass  # Log group already exists, continue

# Set up Python logging
logger = logging.getLogger("backend_logger")
logger.setLevel(logging.INFO)

# Custom logging handler to send logs to CloudWatch
class CloudWatchHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.sequence_token = None

    def emit(self, record):
        log_entry = self.format(record)
        log_event = {"timestamp": int(datetime.utcnow().timestamp() * 1000), "message": log_entry}

        try:
            response = client.put_log_events(
                logGroupName=LOG_GROUP,
                logStreamName=LOG_STREAM,
                logEvents=[log_event],
                sequenceToken=self.sequence_token,
            )
            self.sequence_token = response["nextSequenceToken"]
        except NoCredentialsError:
            print("AWS credentials not configured properly.")
        except Exception as e:
            print(f"Failed to send log to CloudWatch: {e}")

cloudwatch_handler = CloudWatchHandler()
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
cloudwatch_handler.setFormatter(formatter)
logger.addHandler(cloudwatch_handler)

# Middleware for Logging and Error Handling
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Middleware to log all requests and responses.
    """
    logger.info(f"Received request: {request.method} {request.url}")
    try:
        response = await call_next(request)
        logger.info(f"Response status: {response.status_code}")
        return response
    except Exception as e:
        logger.error(f"Error during request handling: {e}")
        raise

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler to log and return custom error responses.
    """
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"message": "An unexpected error occurred. Please try again later."},
    )

# Activity Logging Functions
def log_activity(message: str):
    """
    Log significant user actions, such as trades or deposits.
    """
    logger.info(f"Activity Log: {message}")

# Endpoints with Logging
@app.post("/trade/buy")
def buy_stock(
    ticker: str,
    quantity: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Trade endpoint with logging.
    """
    trade_result = buy_stock(ticker="AAPL", quantity=10, db=db, current_user=current_user)
    log_activity(f"User {current_user.username} initiated a buy trade: {quantity} shares of {ticker}")
    return {"message": f"Successfully bought {quantity} shares of {ticker}"}

@app.post("/cash/deposit")
def deposit_cash(amount: float, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """
    Deposit endpoint with logging.
    """
    deposit_result = deposit_funds(amount=1000, db=db, current_user=current_user)
    log_activity(f"User {current_user.username} deposited {amount:.2f} to their account.")
    return {"message": f"Successfully deposited {amount:.2f}"}

# End

