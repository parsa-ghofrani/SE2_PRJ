from fastapi import FastAPI

from app.api.router import api_router
from app.db.session import SessionLocal
from app.services.matching import rebuild_from_db
from app.api.v1 import admin

app = FastAPI(title="Trading Platform")
app.include_router(api_router, prefix="/api")


app.include_router(admin.router, prefix="/api/v1", tags=["admin"])

@app.on_event("startup")
def startup_rebuild_books():
    db = SessionLocal()
    try:
        rebuild_from_db(db)
        db.commit()  
    finally:
        db.close()



