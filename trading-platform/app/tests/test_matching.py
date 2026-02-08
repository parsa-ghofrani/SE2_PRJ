from app.models.order import Order
from app.services.matching import OrderBook


def test_match_creates_partial_and_filled(db):
    book = OrderBook()

    # SELL 5 @ 100 (id=1)
    sell = Order(user_id=1, symbol="AAPL", side="SELL", type="LIMIT",
                 price=100.0, quantity=5, filled_quantity=0, status="NEW")
    db.add(sell)
    db.flush()

    # BUY 3 @ 120 (id=2) => should match 3 @ 100
    buy = Order(user_id=2, symbol="AAPL", side="BUY", type="LIMIT",
                price=120.0, quantity=3, filled_quantity=0, status="NEW")
    db.add(buy)
    db.flush()

    book.add(sell)
    book.add(buy)
    book.match_all(db, symbol="AAPL")
    db.commit()

    db.refresh(sell)
    db.refresh(buy)

    assert buy.status == "FILLED"
    assert buy.filled_quantity == 3

    assert sell.status == "PARTIAL"
    assert sell.filled_quantity == 3


def test_no_match_when_prices_do_not_cross(db):
    book = OrderBook()

    # SELL 5 @ 150
    sell = Order(user_id=1, symbol="AAPL", side="SELL", type="LIMIT",
                 price=150.0, quantity=5, filled_quantity=0, status="NEW")
    db.add(sell); db.flush()

    # BUY 3 @ 120 (doesn't cross)
    buy = Order(user_id=2, symbol="AAPL", side="BUY", type="LIMIT",
                price=120.0, quantity=3, filled_quantity=0, status="NEW")
    db.add(buy); db.flush()

    book.add(sell)
    book.add(buy)
    book.match_all(db, symbol="AAPL")
    db.commit()

    db.refresh(sell)
    db.refresh(buy)

    assert buy.status == "NEW"
    assert buy.filled_quantity == 0
    assert sell.status == "NEW"
    assert sell.filled_quantity == 0


def test_cancel_prevents_matching(db):
    book = OrderBook()

    sell = Order(user_id=1, symbol="AAPL", side="SELL", type="LIMIT",
                 price=100.0, quantity=5, filled_quantity=0, status="NEW")
    db.add(sell); db.flush()

    buy = Order(user_id=2, symbol="AAPL", side="BUY", type="LIMIT",
                price=120.0, quantity=3, filled_quantity=0, status="NEW")
    db.add(buy); db.flush()

    book.add(sell)
    book.add(buy)

    # cancel the sell in memory
    book.cancel(sell.id)

    book.match_all(db, symbol="AAPL")
    db.commit()

    db.refresh(sell)
    db.refresh(buy)

    # no trade occurs
    assert buy.status == "NEW"
    assert sell.status == "NEW"
