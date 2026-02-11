from fastapi import APIRouter
from app.api.v1.health import router as health_router
from app.api.v1.orders import router as orders_router
from app.api.v1.trades import router as trades_router
from app.api.v1.auth import router as auth_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.stocks import router as stocks_router  # ← اضافه کن


api_router = APIRouter()
api_router.include_router(health_router, prefix="/v1", tags=["health"])
api_router.include_router(auth_router, prefix="/v1", tags=["auth"])
api_router.include_router(stocks_router, prefix="/v1/stocks", tags=["stocks"]) 
api_router.include_router(orders_router, prefix="/v1", tags=["orders"])
api_router.include_router(trades_router, prefix="/v1", tags=["trades"])
api_router.include_router(notifications_router, prefix="/v1/notifications", tags=["notifications"])
