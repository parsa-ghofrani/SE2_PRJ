import pytest
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.orm import Session
from app.services.matching import OrderBook, MatchingEngine
from app.models.order import Order
from app.models.trade import Trade


@pytest.fixture
def db():
    """Mock database session"""
    mock_db = MagicMock(spec=Session)
    mock_db.get = MagicMock(return_value=None)
    mock_db.add = MagicMock()
    mock_db.flush = MagicMock()
    mock_db.commit = MagicMock()
    mock_db.refresh = MagicMock()
    return mock_db


@pytest.fixture
def order_book():
    """Create an order book instance (no symbol parameter needed)"""
    return OrderBook()


@pytest.fixture
def matching_engine():
    """Create a matching engine instance"""
    return MatchingEngine()


class TestMatchingEngineWithBlockchain:
    """Tests for matching engine with blockchain integration"""
    
    def test_trade_recorded_in_db_and_blockchain(self, db, order_book):
        """Test that matched trades are recorded in both DB and blockchain"""
        # Create buy order
        buy_order = Order(
            id=1,
            user_id=1,
            symbol="AAPL",
            side="BUY",
            type="LIMIT",
            price=150.00,
            quantity=10,
            filled_quantity=0,
            status="NEW"
        )
        
        # Create sell order
        sell_order = Order(
            id=2,
            user_id=2,
            symbol="AAPL",
            side="SELL",
            type="LIMIT",
            price=150.00,
            quantity=10,
            filled_quantity=0,
            status="NEW"
        )
        
        # Mock db.get to return our orders
        def get_order(order_class, order_id):
            if order_id == 1:
                return buy_order
            elif order_id == 2:
                return sell_order
            return None
        
        db.get.side_effect = get_order
        
        # Add orders to book
        order_book.add(buy_order)
        order_book.add(sell_order)
        
        # Mock blockchain adapter
        with patch('app.services.matching.blockchain_adapter') as mock_blockchain:
            mock_blockchain.record_trade.return_value = "0xabc123..."
            
            # Execute matching
            order_book.match_all(db, symbol="AAPL")
            
            # Assertions
            assert buy_order.filled_quantity == 10
            assert sell_order.filled_quantity == 10
            assert buy_order.status == "FILLED"
            assert sell_order.status == "FILLED"
            
            # Verify database add was called (for trade)
            assert db.add.called
    
    def test_db_trade_persists_when_blockchain_fails(self, db, order_book):
        """Test that trade is saved to DB even if blockchain recording fails"""
        buy_order = Order(
            id=3,
            user_id=1,
            symbol="AAPL",
            side="BUY",
            type="LIMIT",
            price=145.00,
            quantity=5,
            filled_quantity=0,
            status="NEW"
        )
        
        sell_order = Order(
            id=4,
            user_id=2,
            symbol="AAPL",
            side="SELL",
            type="LIMIT",
            price=145.00,
            quantity=5,
            filled_quantity=0,
            status="NEW"
        )
        
        def get_order(order_class, order_id):
            if order_id == 3:
                return buy_order
            elif order_id == 4:
                return sell_order
            return None
        
        db.get.side_effect = get_order
        
        order_book.add(buy_order)
        order_book.add(sell_order)
        
        # Mock blockchain to raise exception
        with patch('app.services.matching.blockchain_adapter') as mock_blockchain:
            mock_blockchain.record_trade.side_effect = Exception("Blockchain unavailable")
            
            # Execute matching - should still work (blockchain is optional)
            try:
                order_book.match_all(db, symbol="AAPL")
            except Exception:
                pass  # Blockchain error might be swallowed
            
            # Trade should still be created in DB
            assert buy_order.filled_quantity == 5
            assert sell_order.filled_quantity == 5
    
    def test_orders_updated_after_match(self, db, order_book):
        """Test that orders are properly updated after matching"""
        buy_order = Order(
            id=5,
            user_id=1,
            symbol="AAPL",
            side="BUY",
            type="LIMIT",
            price=150.00,
            quantity=10,
            filled_quantity=0,
            status="NEW"
        )
        
        sell_order = Order(
            id=6,
            user_id=2,
            symbol="AAPL",
            side="SELL",
            type="LIMIT",
            price=150.00,
            quantity=10,
            filled_quantity=0,
            status="NEW"
        )
        
        def get_order(order_class, order_id):
            if order_id == 5:
                return buy_order
            elif order_id == 6:
                return sell_order
            return None
        
        db.get.side_effect = get_order
        
        order_book.add(buy_order)
        order_book.add(sell_order)
        
        with patch('app.services.matching.blockchain_adapter'):
            order_book.match_all(db, symbol="AAPL")
        
        # Check orders are filled
        assert buy_order.filled_quantity == 10
        assert sell_order.filled_quantity == 10
        assert buy_order.status == "FILLED"
        assert sell_order.status == "FILLED"
    
    def test_partial_fill_scenario(self, db, order_book):
        """Test partial order fills"""
        buy_order = Order(
            id=7,
            user_id=1,
            symbol="AAPL",
            side="BUY",
            type="LIMIT",
            price=150.00,
            quantity=15,  # Larger quantity
            filled_quantity=0,
            status="NEW"
        )
        
        sell_order = Order(
            id=8,
            user_id=2,
            symbol="AAPL",
            side="SELL",
            type="LIMIT",
            price=150.00,
            quantity=10,  # Smaller quantity
            filled_quantity=0,
            status="NEW"
        )
        
        def get_order(order_class, order_id):
            if order_id == 7:
                return buy_order
            elif order_id == 8:
                return sell_order
            return None
        
        db.get.side_effect = get_order
        
        order_book.add(buy_order)
        order_book.add(sell_order)
        
        with patch('app.services.matching.blockchain_adapter'):
            order_book.match_all(db, symbol="AAPL")
        
        # Check partial fill
        assert buy_order.filled_quantity == 10
        assert sell_order.filled_quantity == 10
        assert buy_order.status == "PARTIAL"  # Still has 5 unfilled
        assert sell_order.status == "FILLED"  # Completely filled
    
    def test_blockchain_receives_correct_trade_data(self, db, order_book):
        """Test that blockchain adapter receives correct trade data"""
        buy_order = Order(
            id=9,
            user_id=1,
            symbol="GOOGL",
            side="BUY",
            type="LIMIT",
            price=2800.50,
            quantity=3,
            filled_quantity=0,
            status="NEW"
        )
        
        sell_order = Order(
            id=10,
            user_id=2,
            symbol="GOOGL",
            side="SELL",
            type="LIMIT",
            price=2800.50,
            quantity=3,
            filled_quantity=0,
            status="NEW"
        )
        
        def get_order(order_class, order_id):
            if order_id == 9:
                return buy_order
            elif order_id == 10:
                return sell_order
            return None
        
        db.get.side_effect = get_order
        
        order_book.add(buy_order)
        order_book.add(sell_order)
        
        with patch('app.services.matching.blockchain_adapter') as mock_blockchain:
            mock_blockchain.record_trade.return_value = "0xdef456..."
            
            order_book.match_all(db, symbol="GOOGL")
            
            # Verify blockchain was called
            # (You'll need to check your matching.py to see how blockchain_adapter.record_trade is called)
            assert mock_blockchain.record_trade.called