from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.models.order import Order
from app.schemas.order import OrderCreate, OrderOut, CancelResult
from app.services.orders import create_order
from app.services.matching import matching_engine

router = APIRouter()


def dev_user_id(x_user_id: int | None) -> int:
    return x_user_id or 1


@router.post("/orders", response_model=OrderOut)
def post_order(
    payload: OrderCreate,
    db: Session = Depends(get_db),
    x_user_id: int | None = Header(default=None, alias="X-User-Id"),
):
    user_id = dev_user_id(x_user_id)
    try:
        order = create_order(db, user_id, payload)
        matching_engine.submit_and_match(db, order)
        db.commit()
        db.refresh(order)
        return order
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        db.rollback()
        raise


@router.get("/orders", response_model=list[OrderOut])
def get_orders(
    db: Session = Depends(get_db),
    x_user_id: int | None = Header(default=None, alias="X-User-Id"),
    symbol: str | None = None,
    status: str | None = None,
):
    user_id = dev_user_id(x_user_id)
    q = db.query(Order).filter(Order.user_id == user_id)
    if symbol:
        q = q.filter(Order.symbol == symbol.upper())
    if status:
        q = q.filter(Order.status == status.upper())
    return q.order_by(Order.created_at.desc()).all()


@router.post("/orders/{order_id}/cancel", response_model=CancelResult)
def cancel_order(
    order_id: int,
    db: Session = Depends(get_db),
    x_user_id: int | None = Header(default=None, alias="X-User-Id"),
):
    user_id = dev_user_id(x_user_id)

    order = db.get(Order, order_id)
    if not order or order.user_id != user_id:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status in ("FILLED", "CANCELLED", "REJECTED"):
        raise HTTPException(status_code=400, detail=f"Cannot cancel order in status={order.status}")

    order.status = "CANCELLED"
    db.commit()

    matching_engine.cancel(order.symbol, order_id)
    return CancelResult(order_id=order_id, status="CANCELLED")
