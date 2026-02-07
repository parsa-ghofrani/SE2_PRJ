from datetime import datetime

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.stock import Stock

DEFAULT_STOCKS = [
    ("AAPL", "Apple Inc.", 185.0),
    ("TSLA", "Tesla, Inc.", 190.0),
    ("AMZN", "Amazon.com, Inc.", 165.0),
    ("MSFT", "Microsoft Corp.", 410.0),
]

def main() -> None:
    db: Session = SessionLocal()
    try:
        now = datetime.utcnow()

        for symbol, name, price in DEFAULT_STOCKS:
            existing = db.get(Stock, symbol)
            if existing:
                existing.name = name
                existing.last_price = price
                existing.updated_at = now
            else:
                db.add(
                    Stock(
                        symbol=symbol,
                        name=name,
                        last_price=price,
                        updated_at=now,
                    )
                )

        db.commit()
        print("✅ Seeded stocks into DB.")
    finally:
        db.close()

if __name__ == "__main__":
    main()
