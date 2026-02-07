from datetime import datetime
from pydantic import BaseModel, Field
from typing import Literal, Optional

Side = Literal["BUY", "SELL"]
OrderType = Literal["LIMIT"]  # Phase 2: only LIMIT to keep matching simple
OrderStatus = Literal["NEW", "PARTIAL", "FILLED", "CANCELLED", "REJECTED"]


class OrderCreate(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=16)
    side: Side
    type: OrderType = "LIMIT"
    price: float = Field(..., gt=0)
    quantity: int = Field(..., gt=0)


class OrderOut(BaseModel):
    id: int
    user_id: int
    symbol: str
    side: Side
    type: OrderType
    price: Optional[float]
    quantity: int
    filled_quantity: int
    status: OrderStatus
    created_at: datetime

    class Config:
        from_attributes = True


class CancelResult(BaseModel):
    order_id: int
    status: OrderStatus
