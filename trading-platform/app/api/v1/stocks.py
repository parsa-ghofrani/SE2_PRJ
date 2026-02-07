from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

# Adjust imports based on your project structure
from app.db.session import get_db
from app.models.stock import Stock
from app.schemas.stock import StockResponse

router = APIRouter()

@router.get("/", response_model=List[StockResponse])
def get_all_stocks(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Get a list of all stocks.
    """
    stocks = db.query(Stock).offset(skip).limit(limit).all()
    return stocks

@router.get("/{symbol}", response_model=StockResponse)
def get_stock(symbol: str, db: Session = Depends(get_db)):
    """
    Get details of a specific stock by its symbol (e.g., AAPL).
    """
    # .get() works because symbol is the primary key in your friend's model
    stock = db.get(Stock, symbol)
    
    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")
    
    return stock