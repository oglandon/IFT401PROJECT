# IFT 401 Proton Backend
# main.py
# Toombs Theobald Tippeconnic

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from Stock_Management_API import app as stock_app
from Trading_Logic import app as trading_app
from Portfolio_Cash_Management import app as portfolio_app
from Transaction_History import app as transaction_app
from Market_Hours_Schedule import app as market_hours_app
from Middleware import app as middleware_app
from Logging_Error_Handling import app as logging_app
from Random_Stock_Price_Gen import update_stock_prices
from User_Auth import router as user_router
from fastapi.middleware.cors import CORSMiddleware
from Random_Stock_Price_Gen import initialize_stock_price_updater


# FastAPI
app = FastAPI(title="Proton Stock Trading System API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],  # Allows all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)

# All routers
app.include_router(user_router, prefix="/user", tags=["User Logic"])
app.include_router(stock_app, prefix="/stocks", tags=["Stock Management"])
app.include_router(trading_app, prefix="/trade", tags=["Trading Logic"])
app.include_router(portfolio_app, prefix="/portfolio", tags=["Portfolio & Cash Management"])
app.include_router(transaction_app, prefix="/transactions", tags=["Transaction History"])
app.include_router(market_hours_app, prefix="/market", tags=["Market Hours & Schedule"])
app.include_router(middleware_app, prefix="/middleware", tags=["Middleware"])
app.include_router(logging_app, prefix="/logging", tags=["Logging & Error Handling"])

# Global Exception Handler 
@app.exception_handler(Exception)
def global_exception_handler(request: Request, exc: Exception):
    """
    Catches all unhandled exceptions and logs them.
    """
    print(f"Unhandled Exception: {exc}")  # Logs to console
    return JSONResponse(status_code=500, content={"message": "Internal Server Error"})

# Periodic Stock Price Updates 
@app.on_event("startup")
def startup_event():
    initialize_stock_price_updater()

# End
