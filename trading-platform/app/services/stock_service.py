"""
Stock Service
Handles business logic for stock operations.
"""
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.stock import Stock


class StockService:
    """Service for managing stock operations."""

    def __init__(self, db: Session):
        self.db = db

    def get_stock(self, symbol: str) -> Optional[Stock]:
        """
        Get a stock by symbol.
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            
        Returns:
            Stock object if found, None otherwise
        """
        return self.db.get(Stock, symbol)

    def list_stocks(self, skip: int = 0, limit: int = 100) -> List[Stock]:
        """
        List all stocks with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of Stock objects
        """
        stmt = select(Stock).offset(skip).limit(limit)
        return list(self.db.scalars(stmt).all())

    def create_stock(
        self,
        symbol: str,
        name: str,
        last_price: float,
    ) -> Stock:
        """
        Create a new stock.
        
        Args:
            symbol: Stock symbol
            name: Company name
            last_price: Current price
            
        Returns:
            Created Stock object
            
        Raises:
            ValueError: If stock already exists
        """
        existing = self.get_stock(symbol)
        if existing:
            raise ValueError(f"Stock with symbol '{symbol}' already exists")

        stock = Stock(
            symbol=symbol,
            name=name,
            last_price=last_price,
            updated_at=datetime.utcnow(),
        )
        self.db.add(stock)
        self.db.commit()
        self.db.refresh(stock)
        return stock

    def update_stock_price(self, symbol: str, new_price: float) -> Optional[Stock]:
        """
        Update stock price.
        
        Args:
            symbol: Stock symbol
            new_price: New price to set
            
        Returns:
            Updated Stock object if found, None otherwise
            
        Raises:
            ValueError: If price is negative
        """
        if new_price < 0:
            raise ValueError("Price cannot be negative")

        stock = self.get_stock(symbol)
        if not stock:
            return None

        stock.last_price = new_price
        stock.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(stock)
        return stock

    def delete_stock(self, symbol: str) -> bool:
        """
        Delete a stock.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            True if deleted, False if not found
        """
        stock = self.get_stock(symbol)
        if not stock:
            return False

        self.db.delete(stock)
        self.db.commit()
        return True

    def search_stocks(self, query: str) -> List[Stock]:
        """
        Search stocks by symbol or name.
        
        Args:
            query: Search query
            
        Returns:
            List of matching Stock objects
        """
        stmt = select(Stock).where(
            (Stock.symbol.ilike(f"%{query}%")) | (Stock.name.ilike(f"%{query}%"))
        )
        return list(self.db.scalars(stmt).all())