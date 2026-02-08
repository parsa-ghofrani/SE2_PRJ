from datetime import datetime
from pydantic import BaseModel

class TradeOut(BaseModel):
    id: int
    buy_order_id: int
    sell_order_id: int
    symbol: str
    price: float
    quantity: int
    executed_at: datetime
    blockchain_tx_hash: str | None = None

    class Config:
        from_attributes = True
