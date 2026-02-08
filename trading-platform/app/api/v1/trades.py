from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.models.trade import Trade
from app.schemas.trade import TradeOut

router = APIRouter()

@router.get("/trades", response_model=list[TradeOut])
def get_trades(db: Session = Depends(get_db), symbol: str | None = None):
    q = db.query(Trade)
    if symbol:
        q = q.filter(Trade.symbol == symbol.upper())
    return q.order_by(Trade.executed_at.desc()).all()
