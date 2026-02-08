from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from typing import Generator  

from app.core.config import settings

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


# 3. Define the Dependency (ADDED BY SABA)
def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()