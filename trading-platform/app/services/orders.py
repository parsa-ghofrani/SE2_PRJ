from sqlalchemy.orm import Session
from app.models.order import Order
from app.schemas.order import OrderCreate


def create_order(db: Session, user_id: int, data: OrderCreate) -> Order:
    # Phase 2: only LIMIT orders
    if data.type != "LIMIT":
        raise ValueError("Only LIMIT orders are supported in Phase 2")
    if data.price is None or data.price <= 0:
        raise ValueError("LIMIT orders require price > 0")
    if data.quantity <= 0:
        raise ValueError("quantity must be > 0")

    order = Order(
        user_id=user_id,
        symbol=data.symbol.upper(),
        side=data.side,
        type=data.type,
        price=data.price,
        quantity=data.quantity,
        filled_quantity=0,
        status="NEW",
    )
    db.add(order)
    db.flush()  # get order.id
    return order
