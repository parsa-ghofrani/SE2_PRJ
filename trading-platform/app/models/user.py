from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)

    wallet_address: Mapped[str | None] = mapped_column(String(64), unique=True, index=True, nullable=True)
    username: Mapped[str | None] = mapped_column(String(50), unique=True, index=True, nullable=True)

    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
