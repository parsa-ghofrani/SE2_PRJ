"""
Stock Schemas for API Request/Response
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class StockBase(BaseModel):
    """Base stock schema."""
    symbol: str = Field(..., min_length=1, max_length=16, description="Stock symbol (e.g., AAPL)")
    name: str = Field(..., min_length=1, max_length=128, description="Company name")
    last_price: float = Field(..., gt=0, description="Current stock price")


class StockCreate(StockBase):
    """Schema for creating a stock."""
    pass


class StockUpdate(BaseModel):
    """Schema for updating a stock."""
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    last_price: Optional[float] = Field(None, gt=0)


class StockResponse(StockBase):
    """Schema for stock response."""
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)