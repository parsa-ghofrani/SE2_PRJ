from fastapi import APIRouter
from app.api.v1.health import router as health_router
from app.api.v1.orders import router as orders_router
from app.api.v1.trades import router as trades_router
from app.api.v1.auth import router as auth_router

api_router = APIRouter()
api_router.include_router(health_router, prefix="/v1", tags=["health"])
api_router.include_router(auth_router, prefix="/v1", tags=["auth"])
api_router.include_router(orders_router, prefix="/v1", tags=["orders"])
api_router.include_router(trades_router, prefix="/v1", tags=["trades"])
