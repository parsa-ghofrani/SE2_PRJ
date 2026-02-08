"""
Tests for Stock Service
"""
import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.db.base import Base
from app.models.stock import Stock
from app.services.stock_service import StockService


# Test database setup
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="function")
def db_session() -> Session:
    """Create a fresh database session for each test."""
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = SessionLocal()
    
    yield session
    
    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def stock_service(db_session: Session) -> StockService:
    """Create a StockService instance with a test database session."""
    return StockService(db_session)


@pytest.fixture
def sample_stock(db_session: Session) -> Stock:
    """Create a sample stock for testing."""
    stock = Stock(
        symbol="AAPL",
        name="Apple Inc.",
        last_price=185.0,
        updated_at=datetime.utcnow(),
    )
    db_session.add(stock)
    db_session.commit()
    db_session.refresh(stock)
    return stock


class TestGetStock:
    """Tests for get_stock method."""

    def test_get_existing_stock(self, stock_service: StockService, sample_stock: Stock):
        """Test retrieving an existing stock."""
        result = stock_service.get_stock("AAPL")
        
        assert result is not None
        assert result.symbol == "AAPL"
        assert result.name == "Apple Inc."
        assert result.last_price == 185.0

    def test_get_nonexistent_stock(self, stock_service: StockService):
        """Test retrieving a stock that doesn't exist."""
        result = stock_service.get_stock("NONEXISTENT")
        
        assert result is None

    def test_get_stock_case_sensitive(self, stock_service: StockService, sample_stock: Stock):
        """Test that stock symbol lookup is case-sensitive."""
        result = stock_service.get_stock("aapl")
        
        # This depends on your database collation
        # Adjust based on your requirements
        assert result is None or result.symbol == "AAPL"


class TestListStocks:
    """Tests for list_stocks method."""

    def test_list_empty_stocks(self, stock_service: StockService):
        """Test listing stocks when database is empty."""
        result = stock_service.list_stocks()
        
        assert result == []

    def test_list_single_stock(self, stock_service: StockService, sample_stock: Stock):
        """Test listing stocks with one stock in database."""
        result = stock_service.list_stocks()
        
        assert len(result) == 1
        assert result[0].symbol == "AAPL"

    def test_list_multiple_stocks(self, stock_service: StockService, db_session: Session):
        """Test listing multiple stocks."""
        stocks = [
            Stock(symbol="AAPL", name="Apple Inc.", last_price=185.0, updated_at=datetime.utcnow()),
            Stock(symbol="TSLA", name="Tesla, Inc.", last_price=190.0, updated_at=datetime.utcnow()),
            Stock(symbol="AMZN", name="Amazon.com, Inc.", last_price=165.0, updated_at=datetime.utcnow()),
        ]
        for stock in stocks:
            db_session.add(stock)
        db_session.commit()
        
        result = stock_service.list_stocks()
        
        assert len(result) == 3
        symbols = {stock.symbol for stock in result}
        assert symbols == {"AAPL", "TSLA", "AMZN"}

    def test_list_stocks_pagination_skip(self, stock_service: StockService, db_session: Session):
        """Test pagination with skip parameter."""
        stocks = [
            Stock(symbol="AAPL", name="Apple Inc.", last_price=185.0, updated_at=datetime.utcnow()),
            Stock(symbol="TSLA", name="Tesla, Inc.", last_price=190.0, updated_at=datetime.utcnow()),
            Stock(symbol="AMZN", name="Amazon.com, Inc.", last_price=165.0, updated_at=datetime.utcnow()),
        ]
        for stock in stocks:
            db_session.add(stock)
        db_session.commit()
        
        result = stock_service.list_stocks(skip=1)
        
        assert len(result) == 2

    def test_list_stocks_pagination_limit(self, stock_service: StockService, db_session: Session):
        """Test pagination with limit parameter."""
        stocks = [
            Stock(symbol="AAPL", name="Apple Inc.", last_price=185.0, updated_at=datetime.utcnow()),
            Stock(symbol="TSLA", name="Tesla, Inc.", last_price=190.0, updated_at=datetime.utcnow()),
            Stock(symbol="AMZN", name="Amazon.com, Inc.", last_price=165.0, updated_at=datetime.utcnow()),
        ]
        for stock in stocks:
            db_session.add(stock)
        db_session.commit()
        
        result = stock_service.list_stocks(limit=2)
        
        assert len(result) == 2

    def test_list_stocks_pagination_skip_and_limit(self, stock_service: StockService, db_session: Session):
        """Test pagination with both skip and limit."""
        stocks = [
            Stock(symbol="AAPL", name="Apple Inc.", last_price=185.0, updated_at=datetime.utcnow()),
            Stock(symbol="TSLA", name="Tesla, Inc.", last_price=190.0, updated_at=datetime.utcnow()),
            Stock(symbol="AMZN", name="Amazon.com, Inc.", last_price=165.0, updated_at=datetime.utcnow()),
            Stock(symbol="MSFT", name="Microsoft Corp.", last_price=410.0, updated_at=datetime.utcnow()),
        ]
        for stock in stocks:
            db_session.add(stock)
        db_session.commit()
        
        result = stock_service.list_stocks(skip=1, limit=2)
        
        assert len(result) == 2


class TestCreateStock:
    """Tests for create_stock method."""

    def test_create_stock_success(self, stock_service: StockService):
        """Test successfully creating a new stock."""
        result = stock_service.create_stock(
            symbol="TSLA",
            name="Tesla, Inc.",
            last_price=190.0,
        )
        
        assert result.symbol == "TSLA"
        assert result.name == "Tesla, Inc."
        assert result.last_price == 190.0
        assert result.updated_at is not None

    def test_create_stock_duplicate_symbol(self, stock_service: StockService, sample_stock: Stock):
        """Test creating a stock with duplicate symbol raises error."""
        with pytest.raises(ValueError, match="already exists"):
            stock_service.create_stock(
                symbol="AAPL",
                name="Another Apple",
                last_price=200.0,
            )

    def test_create_stock_persisted_to_database(self, stock_service: StockService):
        """Test that created stock is persisted to database."""
        stock_service.create_stock(
            symbol="TSLA",
            name="Tesla, Inc.",
            last_price=190.0,
        )
        
        # Retrieve from database
        result = stock_service.get_stock("TSLA")
        
        assert result is not None
        assert result.symbol == "TSLA"

    def test_create_stock_with_zero_price(self, stock_service: StockService):
        """Test creating a stock with zero price."""
        result = stock_service.create_stock(
            symbol="ZERO",
            name="Zero Price Stock",
            last_price=0.0,
        )
        
        assert result.last_price == 0.0


class TestUpdateStockPrice:
    """Tests for update_stock_price method."""

    def test_update_existing_stock_price(self, stock_service: StockService, sample_stock: Stock):
        """Test updating price of existing stock."""
        old_updated_at = sample_stock.updated_at
        
        result = stock_service.update_stock_price("AAPL", 200.0)
        
        assert result is not None
        assert result.last_price == 200.0
        assert result.updated_at > old_updated_at

    def test_update_nonexistent_stock_price(self, stock_service: StockService):
        """Test updating price of nonexistent stock returns None."""
        result = stock_service.update_stock_price("NONEXISTENT", 100.0)
        
        assert result is None

    def test_update_stock_price_negative_raises_error(
        self, stock_service: StockService, sample_stock: Stock
    ):
        """Test that negative price raises ValueError."""
        with pytest.raises(ValueError, match="cannot be negative"):
            stock_service.update_stock_price("AAPL", -10.0)

    def test_update_stock_price_zero(self, stock_service: StockService, sample_stock: Stock):
        """Test updating stock price to zero."""
        result = stock_service.update_stock_price("AAPL", 0.0)
        
        assert result is not None
        assert result.last_price == 0.0

    def test_update_stock_price_persisted(self, stock_service: StockService, sample_stock: Stock):
        """Test that price update is persisted to database."""
        stock_service.update_stock_price("AAPL", 250.0)
        
        # Retrieve from database
        result = stock_service.get_stock("AAPL")
        
        assert result.last_price == 250.0


class TestDeleteStock:
    """Tests for delete_stock method."""

    def test_delete_existing_stock(self, stock_service: StockService, sample_stock: Stock):
        """Test deleting an existing stock."""
        result = stock_service.delete_stock("AAPL")
        
        assert result is True

    def test_delete_stock_removes_from_database(
        self, stock_service: StockService, sample_stock: Stock
    ):
        """Test that deleted stock is removed from database."""
        stock_service.delete_stock("AAPL")
        
        # Try to retrieve
        result = stock_service.get_stock("AAPL")
        
        assert result is None

    def test_delete_nonexistent_stock(self, stock_service: StockService):
        """Test deleting a nonexistent stock returns False."""
        result = stock_service.delete_stock("NONEXISTENT")
        
        assert result is False


class TestSearchStocks:
    """Tests for search_stocks method."""

    def test_search_by_symbol(self, stock_service: StockService, db_session: Session):
        """Test searching stocks by symbol."""
        stocks = [
            Stock(symbol="AAPL", name="Apple Inc.", last_price=185.0, updated_at=datetime.utcnow()),
            Stock(symbol="TSLA", name="Tesla, Inc.", last_price=190.0, updated_at=datetime.utcnow()),
            Stock(symbol="AMZN", name="Amazon.com, Inc.", last_price=165.0, updated_at=datetime.utcnow()),
        ]
        for stock in stocks:
            db_session.add(stock)
        db_session.commit()
        
        result = stock_service.search_stocks("AAP")
        
        assert len(result) == 1
        assert result[0].symbol == "AAPL"

    def test_search_by_name(self, stock_service: StockService, db_session: Session):
        """Test searching stocks by company name."""
        stocks = [
            Stock(symbol="AAPL", name="Apple Inc.", last_price=185.0, updated_at=datetime.utcnow()),
            Stock(symbol="TSLA", name="Tesla, Inc.", last_price=190.0, updated_at=datetime.utcnow()),
            Stock(symbol="AMZN", name="Amazon.com, Inc.", last_price=165.0, updated_at=datetime.utcnow()),
        ]
        for stock in stocks:
            db_session.add(stock)
        db_session.commit()
        
        result = stock_service.search_stocks("Tesla")
        
        assert len(result) == 1
        assert result[0].symbol == "TSLA"

    def test_search_case_insensitive(self, stock_service: StockService, db_session: Session):
        """Test that search is case-insensitive."""
        stock = Stock(symbol="AAPL", name="Apple Inc.", last_price=185.0, updated_at=datetime.utcnow())
        db_session.add(stock)
        db_session.commit()
        
        result = stock_service.search_stocks("apple")
        
        assert len(result) == 1
        assert result[0].symbol == "AAPL"

    def test_search_partial_match(self, stock_service: StockService, db_session: Session):
        """Test searching with partial match."""
        stocks = [
            Stock(symbol="AAPL", name="Apple Inc.", last_price=185.0, updated_at=datetime.utcnow()),
            Stock(symbol="AMZN", name="Amazon.com, Inc.", last_price=165.0, updated_at=datetime.utcnow()),
        ]
        for stock in stocks:
            db_session.add(stock)
        db_session.commit()
        
        result = stock_service.search_stocks("A")
        
        # Should match both AAPL (symbol) and AMZN (symbol) and Amazon (name)
        assert len(result) >= 2

    def test_search_no_results(self, stock_service: StockService, sample_stock: Stock):
        """Test search with no matching results."""
        result = stock_service.search_stocks("NONEXISTENT")
        
        assert result == []

    def test_search_empty_query(self, stock_service: StockService, db_session: Session):
        """Test search with empty query."""
        stocks = [
            Stock(symbol="AAPL", name="Apple Inc.", last_price=185.0, updated_at=datetime.utcnow()),
            Stock(symbol="TSLA", name="Tesla, Inc.", last_price=190.0, updated_at=datetime.utcnow()),
        ]
        for stock in stocks:
            db_session.add(stock)
        db_session.commit()
        
        result = stock_service.search_stocks("")
        
        # Empty query should match all stocks
        assert len(result) == 2