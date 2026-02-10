from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import heapq
import threading

from sqlalchemy.orm import Session

from app.models.order import Order
from app.models.trade import Trade
from app.services.blockchain import blockchain_adapter


def rebuild_from_db(db: Session) -> None:
    open_orders = (
        db.query(Order)
        .filter(Order.status.in_(("NEW", "PARTIAL")))
        .order_by(Order.created_at.asc())
        .all()
    )

    for o in open_orders:
        book = matching_engine._book(o.symbol)  # internal
        with book.lock:
            book.add(o)


@dataclass
class BookEntry:
    order_id: int
    side: str          # BUY/SELL
    price: float
    remaining: int
    seq: int
    cancelled: bool = False


class OrderBook:
    """
    BUY: highest price first (max-heap) => store (-price, seq, order_id)
    SELL: lowest price first (min-heap) => store ( price, seq, order_id)
    """
    def __init__(self) -> None:
        self.bids: List[Tuple[float, int, int]] = []
        self.asks: List[Tuple[float, int, int]] = []
        self.entries: Dict[int, BookEntry] = {}
        self.lock = threading.Lock()
        self.seq_counter = 0

    def _next_seq(self) -> int:
        self.seq_counter += 1
        return self.seq_counter

    def add(self, order: Order) -> None:
        if order.price is None:
            raise ValueError("LIMIT order requires price")

        remaining = int(order.quantity - order.filled_quantity)
        if remaining <= 0:
            return

        e = BookEntry(
            order_id=int(order.id),
            side=str(order.side),
            price=float(order.price),
            remaining=remaining,
            seq=self._next_seq(),
        )
        self.entries[order.id] = e

        if order.side == "BUY":
            heapq.heappush(self.bids, (-e.price, e.seq, e.order_id))
        else:
            heapq.heappush(self.asks, (e.price, e.seq, e.order_id))

    def cancel(self, order_id: int) -> bool:
        e = self.entries.get(order_id)
        if not e:
            return False
        e.cancelled = True
        return True

    def _top_valid_bid(self) -> Optional[BookEntry]:
        while self.bids:
            _, _, oid = self.bids[0]
            e = self.entries.get(oid)
            if not e or e.cancelled or e.remaining <= 0:
                heapq.heappop(self.bids)
                continue
            return e
        return None

    def _top_valid_ask(self) -> Optional[BookEntry]:
        while self.asks:
            _, _, oid = self.asks[0]
            e = self.entries.get(oid)
            if not e or e.cancelled or e.remaining <= 0:
                heapq.heappop(self.asks)
                continue
            return e
        return None

    def match_all(self, db: Session, symbol: str) -> None:
        """
        Matching rule:
        - match if best_bid.price >= best_ask.price
        - trade price = ask price (simple)
        """
        while True:
            bid = self._top_valid_bid()
            ask = self._top_valid_ask()
            if not bid or not ask:
                return
            if bid.price < ask.price:
                return

            qty = min(bid.remaining, ask.remaining)
            trade_price = ask.price

            buy_order = db.get(Order, bid.order_id)
            sell_order = db.get(Order, ask.order_id)
            if not buy_order or not sell_order:
                bid.remaining = 0
                ask.remaining = 0
                continue

            # skip cancelled in DB
            if buy_order.status == "CANCELLED":
                bid.cancelled = True
                continue
            if sell_order.status == "CANCELLED":
                ask.cancelled = True
                continue

            # 1) Create trade row first (so it gets an ID)
            trade = Trade(
                buy_order_id=buy_order.id,
                sell_order_id=sell_order.id,
                symbol=symbol,
                price=trade_price,
                quantity=qty,
            )
            db.add(trade)
            db.flush()  # trade.id becomes available here

            # 2) Record on blockchain (idempotent-ish: if we somehow re-run, adapter/contract can reject)
            # Best-effort: do NOT raise; leave blockchain_tx_hash = NULL so you can retry later.
            try:
                tx_hash = blockchain_adapter.record_trade(
                    trade_id=int(trade.id),
                    symbol=str(trade.symbol),
                    price=float(trade.price),
                    quantity=int(trade.quantity),
                    buy_order_id=int(trade.buy_order_id),
                    sell_order_id=int(trade.sell_order_id),
                )
                trade.blockchain_tx_hash = tx_hash
                db.flush()
            except Exception:
                # keep DB trade, but without tx hash
                pass

            # 3) Update orders
            buy_order.filled_quantity += qty
            sell_order.filled_quantity += qty

            buy_order.status = "FILLED" if buy_order.filled_quantity >= buy_order.quantity else "PARTIAL"
            sell_order.status = "FILLED" if sell_order.filled_quantity >= sell_order.quantity else "PARTIAL"

            # 4) Update in-memory remaining
            bid.remaining -= qty
            ask.remaining -= qty

            if bid.remaining <= 0:
                heapq.heappop(self.bids)
            if ask.remaining <= 0:
                heapq.heappop(self.asks)


class MatchingEngine:
    def __init__(self) -> None:
        self.books: Dict[str, OrderBook] = {}
        self.global_lock = threading.Lock()

    def _book(self, symbol: str) -> OrderBook:
        with self.global_lock:
            if symbol not in self.books:
                self.books[symbol] = OrderBook()
            return self.books[symbol]

    def submit_and_match(self, db: Session, order: Order) -> None:
        symbol = order.symbol
        book = self._book(symbol)
        with book.lock:
            book.add(order)
            book.match_all(db, symbol)

    def cancel(self, symbol: str, order_id: int) -> bool:
        book = self.books.get(symbol)
        if not book:
            return False
        with book.lock:
            return book.cancel(order_id)


matching_engine = MatchingEngine()
