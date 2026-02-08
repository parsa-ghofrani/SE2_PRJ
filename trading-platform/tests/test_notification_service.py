"""
Tests for Notification Service
"""
import pytest
import json
from datetime import datetime
from unittest.mock import Mock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from passlib.context import CryptContext

from app.db.base import Base
from app.models.notification import Notification
from app.models.user import User
from app.services.notification_service import NotificationService


# Test database setup
TEST_DATABASE_URL = "sqlite:///:memory:"

# Initialize password context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


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
def notification_service(db_session: Session) -> NotificationService:
    """Create a NotificationService instance with a test database session."""
    # ← CHANGED: Mock the message_broker.publish to avoid Redis connection
    with patch('app.services.notification_service.message_broker') as mock_broker:
        mock_broker.publish = Mock()  # Mock the publish method
        service = NotificationService(db_session)
        yield service


@pytest.fixture
def sample_user(db_session: Session) -> User:
    """Create a sample user for testing."""
    user = User(
        id=1,
        username="testuser",
        wallet_address="0x1234567890abcdef",
        password_hash=pwd_context.hash("testpassword123")
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def sample_notification(db_session: Session, sample_user: User) -> Notification:
    """Create a sample notification for testing."""
    notification = Notification(
        user_id=sample_user.id,
        type="ORDER",
        title="Test Notification",
        message="This is a test notification",
        data=json.dumps({"order_id": 123}),
        is_read=False,
        created_at=datetime.utcnow(),
    )
    db_session.add(notification)
    db_session.commit()
    db_session.refresh(notification)
    return notification


class TestCreateNotification:
    """Tests for create_notification method."""

    @patch('app.services.notification_service.message_broker')
    def test_create_notification_success(
        self, mock_broker, db_session: Session, sample_user: User
    ):
        """Test successfully creating a notification."""
        mock_broker.publish = Mock()
        notification_service = NotificationService(db_session)
        
        notification = notification_service.create_notification(
            user_id=sample_user.id,
            notification_type="TRADE",
            title="Trade Executed",
            message="Your trade was executed successfully",
            data={"trade_id": 456, "price": 100.50},
        )
        
        assert notification.id is not None
        assert notification.user_id == sample_user.id
        assert notification.type == "TRADE"
        assert notification.title == "Trade Executed"
        assert notification.message == "Your trade was executed successfully"
        assert notification.is_read is False
        assert notification.created_at is not None
        
        # Check data was serialized
        data = json.loads(notification.data)
        assert data["trade_id"] == 456
        assert data["price"] == 100.50
        
        # Verify message broker was called
        mock_broker.publish.assert_called_once()

    @patch('app.services.notification_service.message_broker')
    def test_create_notification_without_data(
        self, mock_broker, db_session: Session, sample_user: User
    ):
        """Test creating a notification without extra data."""
        mock_broker.publish = Mock()
        notification_service = NotificationService(db_session)
        
        notification = notification_service.create_notification(
            user_id=sample_user.id,
            notification_type="ANNOUNCEMENT",
            title="System Update",
            message="The system will be updated tonight",
        )
        
        assert notification.data is None
        assert notification.type == "ANNOUNCEMENT"

    @patch('app.services.notification_service.message_broker')
    def test_create_notification_persisted(
        self, mock_broker, db_session: Session, sample_user: User
    ):
        """Test that created notification is persisted to database."""
        mock_broker.publish = Mock()
        notification_service = NotificationService(db_session)
        
        notification = notification_service.create_notification(
            user_id=sample_user.id,
            notification_type="POSITION",
            title="Position Update",
            message="Your position has changed",
        )
        
        # Retrieve from database
        retrieved = notification_service.db.get(Notification, notification.id)
        
        assert retrieved is not None
        assert retrieved.id == notification.id
        assert retrieved.title == "Position Update"


# Keep all the other test classes unchanged - they don't use create_notification
# so they don't need mocking

class TestGetUserNotifications:
    """Tests for get_user_notifications method."""

    @patch('app.services.notification_service.message_broker')
    def test_get_notifications_empty(
        self, mock_broker, db_session: Session, sample_user: User
    ):
        """Test getting notifications when user has none."""
        notification_service = NotificationService(db_session)
        notifications = notification_service.get_user_notifications(sample_user.id)
        
        assert notifications == []

    @patch('app.services.notification_service.message_broker')
    def test_get_single_notification(
        self, mock_broker, db_session: Session, sample_user: User
    ):
        """Test getting a single notification."""
        notification_service = NotificationService(db_session)
        
        # Create notification directly
        notification = Notification(
            user_id=sample_user.id,
            type="ORDER",
            title="Test Notification",
            message="This is a test notification",
            data=json.dumps({"order_id": 123}),
            is_read=False,
            created_at=datetime.utcnow(),
        )
        db_session.add(notification)
        db_session.commit()
        
        notifications = notification_service.get_user_notifications(sample_user.id)
        
        assert len(notifications) == 1
        assert notifications[0].id == notification.id

    @patch('app.services.notification_service.message_broker')
    def test_get_multiple_notifications(
        self, mock_broker, notification_service: NotificationService, sample_user: User, db_session: Session
    ):
        """Test getting multiple notifications."""
        # Create 3 notifications
        for i in range(3):
            notif = Notification(
                user_id=sample_user.id,
                type="ORDER",
                title=f"Notification {i}",
                message=f"Message {i}",
                is_read=False,
                created_at=datetime.utcnow(),
            )
            db_session.add(notif)
        db_session.commit()
        
        notifications = notification_service.get_user_notifications(sample_user.id)
        
        assert len(notifications) == 3

    @patch('app.services.notification_service.message_broker')
    def test_get_notifications_unread_only(
        self, mock_broker, notification_service: NotificationService, sample_user: User, db_session: Session
    ):
        """Test filtering for unread notifications only."""
        # Create 2 read and 3 unread notifications
        for i in range(5):
            notif = Notification(
                user_id=sample_user.id,
                type="ORDER",
                title=f"Notification {i}",
                message=f"Message {i}",
                is_read=(i < 2),  # First 2 are read
                created_at=datetime.utcnow(),
            )
            db_session.add(notif)
        db_session.commit()
        
        notifications = notification_service.get_user_notifications(
            sample_user.id, unread_only=True
        )
        
        assert len(notifications) == 3
        for notif in notifications:
            assert notif.is_read is False

    @patch('app.services.notification_service.message_broker')
    def test_get_notifications_pagination_skip(
        self, mock_broker, notification_service: NotificationService, sample_user: User, db_session: Session
    ):
        """Test pagination with skip parameter."""
        # Create 5 notifications
        for i in range(5):
            notif = Notification(
                user_id=sample_user.id,
                type="ORDER",
                title=f"Notification {i}",
                message=f"Message {i}",
                is_read=False,
                created_at=datetime.utcnow(),
            )
            db_session.add(notif)
        db_session.commit()
        
        notifications = notification_service.get_user_notifications(
            sample_user.id, skip=2
        )
        
        assert len(notifications) == 3

    @patch('app.services.notification_service.message_broker')
    def test_get_notifications_pagination_limit(
        self, mock_broker, notification_service: NotificationService, sample_user: User, db_session: Session
    ):
        """Test pagination with limit parameter."""
        # Create 5 notifications
        for i in range(5):
            notif = Notification(
                user_id=sample_user.id,
                type="ORDER",
                title=f"Notification {i}",
                message=f"Message {i}",
                is_read=False,
                created_at=datetime.utcnow(),
            )
            db_session.add(notif)
        db_session.commit()
        
        notifications = notification_service.get_user_notifications(
            sample_user.id, limit=2
        )
        
        assert len(notifications) == 2

    @patch('app.services.notification_service.message_broker')
    def test_get_notifications_ordered_by_date(
        self, mock_broker, notification_service: NotificationService, sample_user: User, db_session: Session
    ):
        """Test that notifications are ordered by created_at descending."""
        # Create notifications with different timestamps
        for i in range(3):
            notif = Notification(
                user_id=sample_user.id,
                type="ORDER",
                title=f"Notification {i}",
                message=f"Message {i}",
                is_read=False,
                created_at=datetime.utcnow(),
            )
            db_session.add(notif)
        db_session.commit()
        
        notifications = notification_service.get_user_notifications(sample_user.id)
        
        # Check they're in descending order
        for i in range(len(notifications) - 1):
            assert notifications[i].created_at >= notifications[i + 1].created_at


class TestMarkAsRead:
    """Tests for mark_as_read method."""

    @patch('app.services.notification_service.message_broker')
    def test_mark_notification_as_read(
        self, mock_broker, notification_service: NotificationService, sample_notification: Notification
    ):
        """Test marking a notification as read."""
        assert sample_notification.is_read is False
        assert sample_notification.read_at is None
        
        updated = notification_service.mark_as_read(
            sample_notification.id, sample_notification.user_id
        )
        
        assert updated is not None
        assert updated.is_read is True
        assert updated.read_at is not None

    @patch('app.services.notification_service.message_broker')
    def test_mark_as_read_wrong_user(
        self, mock_broker, notification_service: NotificationService, sample_notification: Notification
    ):
        """Test that marking as read fails for wrong user."""
        result = notification_service.mark_as_read(
            sample_notification.id, user_id=999
        )
        
        assert result is None

    @patch('app.services.notification_service.message_broker')
    def test_mark_as_read_nonexistent(
        self, mock_broker, notification_service: NotificationService
    ):
        """Test marking a nonexistent notification as read."""
        result = notification_service.mark_as_read(9999, user_id=1)
        
        assert result is None

    @patch('app.services.notification_service.message_broker')
    def test_mark_as_read_persisted(
        self, mock_broker, notification_service: NotificationService, sample_notification: Notification
    ):
        """Test that mark as read is persisted to database."""
        notification_service.mark_as_read(
            sample_notification.id, sample_notification.user_id
        )
        
        # Retrieve from database
        retrieved = notification_service.db.get(Notification, sample_notification.id)
        
        assert retrieved.is_read is True


class TestMarkAllAsRead:
    """Tests for mark_all_as_read method."""

    @patch('app.services.notification_service.message_broker')
    def test_mark_all_as_read(
        self, mock_broker, notification_service: NotificationService, sample_user: User, db_session: Session
    ):
        """Test marking all notifications as read."""
        # Create 3 unread notifications
        for i in range(3):
            notif = Notification(
                user_id=sample_user.id,
                type="ORDER",
                title=f"Notification {i}",
                message=f"Message {i}",
                is_read=False,
                created_at=datetime.utcnow(),
            )
            db_session.add(notif)
        db_session.commit()
        
        count = notification_service.mark_all_as_read(sample_user.id)
        
        assert count == 3
        
        # Verify all are read
        notifications = notification_service.get_user_notifications(sample_user.id)
        for notif in notifications:
            assert notif.is_read is True

    @patch('app.services.notification_service.message_broker')
    def test_mark_all_as_read_no_unread(
        self, mock_broker, notification_service: NotificationService, sample_user: User
    ):
        """Test marking all as read when there are no unread notifications."""
        count = notification_service.mark_all_as_read(sample_user.id)
        
        assert count == 0

    @patch('app.services.notification_service.message_broker')
    def test_mark_all_as_read_only_unread(
        self, mock_broker, notification_service: NotificationService, sample_user: User, db_session: Session
    ):
        """Test that mark all only affects unread notifications."""
        # Create 2 read and 3 unread
        for i in range(5):
            notif = Notification(
                user_id=sample_user.id,
                type="ORDER",
                title=f"Notification {i}",
                message=f"Message {i}",
                is_read=(i < 2),
                created_at=datetime.utcnow(),
            )
            db_session.add(notif)
        db_session.commit()
        
        count = notification_service.mark_all_as_read(sample_user.id)
        
        assert count == 3


class TestDeleteNotification:
    """Tests for delete_notification method."""

    @patch('app.services.notification_service.message_broker')
    def test_delete_notification_success(
        self, mock_broker, notification_service: NotificationService, sample_notification: Notification
    ):
        """Test successfully deleting a notification."""
        result = notification_service.delete_notification(
            sample_notification.id, sample_notification.user_id
        )
        
        assert result is True
        
        # Verify it's deleted
        retrieved = notification_service.db.get(Notification, sample_notification.id)
        assert retrieved is None

    @patch('app.services.notification_service.message_broker')
    def test_delete_notification_wrong_user(
        self, mock_broker, notification_service: NotificationService, sample_notification: Notification
    ):
        """Test that deleting fails for wrong user."""
        result = notification_service.delete_notification(
            sample_notification.id, user_id=999
        )
        
        assert result is False

    @patch('app.services.notification_service.message_broker')
    def test_delete_nonexistent_notification(
        self, mock_broker, notification_service: NotificationService
    ):
        """Test deleting a nonexistent notification."""
        result = notification_service.delete_notification(9999, user_id=1)
        
        assert result is False


class TestGetUnreadCount:
    """Tests for get_unread_count method."""

    @patch('app.services.notification_service.message_broker')
    def test_get_unread_count_zero(
        self, mock_broker, notification_service: NotificationService, sample_user: User
    ):
        """Test getting unread count when there are none."""
        count = notification_service.get_unread_count(sample_user.id)
        
        assert count == 0

    @patch('app.services.notification_service.message_broker')
    def test_get_unread_count_with_unread(
        self, mock_broker, notification_service: NotificationService, sample_user: User, db_session: Session
    ):
        """Test getting unread count with unread notifications."""
        # Create 2 read and 3 unread
        for i in range(5):
            notif = Notification(
                user_id=sample_user.id,
                type="ORDER",
                title=f"Notification {i}",
                message=f"Message {i}",
                is_read=(i < 2),
                created_at=datetime.utcnow(),
            )
            db_session.add(notif)
        db_session.commit()
        
        count = notification_service.get_unread_count(sample_user.id)
        
        assert count == 3

    @patch('app.services.notification_service.message_broker')
    def test_get_unread_count_all_read(
        self, mock_broker, notification_service: NotificationService, sample_user: User, db_session: Session
    ):
        """Test getting unread count when all are read."""
        # Create 3 read notifications
        for i in range(3):
            notif = Notification(
                user_id=sample_user.id,
                type="ORDER",
                title=f"Notification {i}",
                message=f"Message {i}",
                is_read=True,
                created_at=datetime.utcnow(),
            )
            db_session.add(notif)
        db_session.commit()
        
        count = notification_service.get_unread_count(sample_user.id)
        
        assert count == 0