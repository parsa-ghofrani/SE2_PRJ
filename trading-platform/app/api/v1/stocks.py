"""
Stock API Endpoints
Manage stocks/symbols in the trading platform
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.models.stock import Stock
from app.schemas.stock import StockCreate, StockUpdate, StockResponse

router = APIRouter()


@router.get("/", response_model=List[StockResponse])
def get_stocks(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records"),
    db: Session = Depends(get_db),
):
    """
    Get all available stocks.
    
    - **skip**: Pagination offset
    - **limit**: Maximum results per page
    """
    stocks = db.query(Stock).offset(skip).limit(limit).all()
    return stocks


@router.get("/{symbol}", response_model=StockResponse)
def get_stock(
    symbol: str,
    db: Session = Depends(get_db),
):
    """
    Get a specific stock by symbol.
    
    - **symbol**: Stock symbol (e.g., AAPL, TSLA)
    """
    stock = db.query(Stock).filter(Stock.symbol == symbol.upper()).first()
    
    if not stock:
        raise HTTPException(
            status_code=404,
            detail=f"Stock with symbol '{symbol}' not found"
        )
    
    return stock


@router.post("/", response_model=StockResponse, status_code=201)
def create_stock(
    stock: StockCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new stock (Admin only - TODO: add auth check).
    
    - **symbol**: Stock symbol (e.g., AAPL)
    - **name**: Company name
    - **last_price**: Current price
    """
    # Check if stock already exists
    existing = db.query(Stock).filter(Stock.symbol == stock.symbol.upper()).first()
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Stock with symbol '{stock.symbol}' already exists"
        )
    
    # Create new stock
    from datetime import datetime
    db_stock = Stock(
        symbol=stock.symbol.upper(),
        name=stock.name,
        last_price=stock.last_price,
        updated_at=datetime.utcnow(),
    )
    
    db.add(db_stock)
    db.commit()
    db.refresh(db_stock)
    
    return db_stock


@router.put("/{symbol}", response_model=StockResponse)
def update_stock(
    symbol: str,
    stock_update: StockUpdate,
    db: Session = Depends(get_db),
):
    """
    Update stock information (Admin only - TODO: add auth check).
    
    - **symbol**: Stock symbol to update
    - **name**: New company name (optional)
    - **last_price**: New price (optional)
    """
    db_stock = db.query(Stock).filter(Stock.symbol == symbol.upper()).first()
    
    if not db_stock:
        raise HTTPException(
            status_code=404,
            detail=f"Stock with symbol '{symbol}' not found"
        )
    
    # Update fields if provided
    from datetime import datetime
    
    if stock_update.name is not None:
        db_stock.name = stock_update.name
    
    if stock_update.last_price is not None:
        db_stock.last_price = stock_update.last_price
    
    db_stock.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(db_stock)
    
    return db_stock


@router.delete("/{symbol}")
def delete_stock(
    symbol: str,
    db: Session = Depends(get_db),
):
    """
    Delete a stock (Admin only - TODO: add auth check).
    
    - **symbol**: Stock symbol to delete
    """
    db_stock = db.query(Stock).filter(Stock.symbol == symbol.upper()).first()
    
    if not db_stock:
        raise HTTPException(
            status_code=404,
            detail=f"Stock with symbol '{symbol}' not found"
        )
    
    db.delete(db_stock)
    db.commit()
    
    return {"message": f"Stock '{symbol}' deleted successfully"}


@router.get("/{symbol}/price", response_model=dict)
def get_stock_price(
    symbol: str,
    db: Session = Depends(get_db),
):
    """
    Get current price of a stock.
    
    - **symbol**: Stock symbol
    """
    stock = db.query(Stock).filter(Stock.symbol == symbol.upper()).first()
    
    if not stock:
        raise HTTPException(
            status_code=404,
            detail=f"Stock with symbol '{symbol}' not found"
        )
    
    return {
        "symbol": stock.symbol,
        "last_price": stock.last_price,
        "updated_at": stock.updated_at,
    }