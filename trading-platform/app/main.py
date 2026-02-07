from fastapi import FastAPI

from app.api.router import api_router
from app.db.session import SessionLocal
from app.services.matching import rebuild_from_db

app = FastAPI(title="Trading Platform")
app.include_router(api_router, prefix="/api")


@app.on_event("startup")
def startup_rebuild_books():
    db = SessionLocal()
    try:
        rebuild_from_db(db)
        db.commit()  # safe (rebuild shouldn't change DB, but harmless)
    finally:
        db.close()
