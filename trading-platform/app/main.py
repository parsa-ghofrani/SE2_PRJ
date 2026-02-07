from fastapi import FastAPI
from app.api.router import api_router

app = FastAPI(title="Trading Platform")

app.include_router(api_router, prefix="/api")
