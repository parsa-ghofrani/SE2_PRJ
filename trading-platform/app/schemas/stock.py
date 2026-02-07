from pydantic import BaseModel, ConfigDict
from datetime import datetime

# Base class with shared fields
class StockBase(BaseModel):
    symbol: str
    name: str
    last_price: float

# Class for creating a stock (if needed later)
class StockCreate(StockBase):
    pass

# Class for reading a stock (includes timestamp)
class StockResponse(StockBase):
    updated_at: datetime

    # This allows Pydantic to read data directly from the SQLAlchemy model
    model_config = ConfigDict(from_attributes=True)