"""
Notification Service
Handles creating and managing user notifications
"""
from datetime import datetime
from typing import List, Optional
import json

from sqlalchemy.orm import Session
from sqlalchemy import select, and_

from app.models.notification import Notification
from app.core.message_broker import message_broker


class NotificationService:
    """Service for managing notifications."""

    def __init__(self, db: Session):
        self.db = db

    def create_notification(
        self,
        user_id: int,
        notification_type: str,
        title: str,
        message: str,
        data: Optional[dict] = None,
    ) -> Notification:
        """
        Create a new notification for a user.
        
        Args:
            user_id: User ID to notify
            notification_type: Type (ORDER, TRADE, ANNOUNCEMENT, POSITION)
            title: Notification title
            message: Notification message
            data: Optional extra data as dict
            
        Returns:
            Created Notification object
        """
        notification = Notification(
            user_id=user_id,
            type=notification_type,
            title=title,
            message=message,
            data=json.dumps(data) if data else None,
            is_read=False,
            created_at=datetime.utcnow(),
        )
        
        self.db.add(notification)
        self.db.commit()
        self.db.refresh(notification)
        
        # Publish to message broker for real-time delivery
        message_broker.publish('notifications', {
            'user_id': user_id,
            'notification_id': notification.id,
            'type': notification_type,
            'title': title,
            'message': message,
        })
        
        return notification

    def get_user_notifications(
        self,
        user_id: int,
        unread_only: bool = False,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Notification]:
        """
        Get notifications for a user.
        
        Args:
            user_id: User ID
            unread_only: If True, only return unread notifications
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of Notification objects
        """
        stmt = select(Notification).where(Notification.user_id == user_id)
        
        if unread_only:
            stmt = stmt.where(Notification.is_read == False)
        
        stmt = stmt.order_by(Notification.created_at.desc()).offset(skip).limit(limit)
        
        return list(self.db.scalars(stmt).all())

    def mark_as_read(self, notification_id: int, user_id: int) -> Optional[Notification]:
        """
        Mark a notification as read.
        
        Args:
            notification_id: Notification ID
            user_id: User ID (for security check)
            
        Returns:
            Updated Notification if found, None otherwise
        """
        stmt = select(Notification).where(
            and_(
                Notification.id == notification_id,
                Notification.user_id == user_id
            )
        )
        notification = self.db.scalar(stmt)
        
        if not notification:
            return None
        
        notification.is_read = True
        notification.read_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(notification)
        
        return notification

    def mark_all_as_read(self, user_id: int) -> int:
        """
        Mark all notifications as read for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Number of notifications updated
        """
        stmt = select(Notification).where(
            and_(
                Notification.user_id == user_id,
                Notification.is_read == False
            )
        )
        notifications = self.db.scalars(stmt).all()
        
        count = 0
        now = datetime.utcnow()
        for notification in notifications:
            notification.is_read = True
            notification.read_at = now
            count += 1
        
        self.db.commit()
        return count

    def delete_notification(self, notification_id: int, user_id: int) -> bool:
        """
        Delete a notification.
        
        Args:
            notification_id: Notification ID
            user_id: User ID (for security check)
            
        Returns:
            True if deleted, False if not found
        """
        stmt = select(Notification).where(
            and_(
                Notification.id == notification_id,
                Notification.user_id == user_id
            )
        )
        notification = self.db.scalar(stmt)
        
        if not notification:
            return False
        
        self.db.delete(notification)
        self.db.commit()
        return True

    def get_unread_count(self, user_id: int) -> int:
        """
        Get count of unread notifications for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Count of unread notifications
        """
        stmt = select(Notification).where(
            and_(
                Notification.user_id == user_id,
                Notification.is_read == False
            )
        )
        return len(list(self.db.scalars(stmt).all()))


# Event Handlers (called when events are published)

def handle_order_created(db: Session, order_data: dict) -> None:
    """Handle order created event."""
    service = NotificationService(db)
    service.create_notification(
        user_id=order_data['user_id'],
        notification_type='ORDER',
        title='Order Placed',
        message=f"Your {order_data['side']} order for {order_data['quantity']} shares of {order_data['symbol']} has been placed.",
        data=order_data
    )


def handle_trade_executed(db: Session, trade_data: dict) -> None:
    """Handle trade executed event."""
    service = NotificationService(db)
    
    # Notify buyer
    service.create_notification(
        user_id=trade_data['buyer_id'],
        notification_type='TRADE',
        title='Trade Executed',
        message=f"Your BUY order for {trade_data['quantity']} shares of {trade_data['symbol']} was executed at ${trade_data['price']}.",
        data=trade_data
    )
    
    # Notify seller
    service.create_notification(
        user_id=trade_data['seller_id'],
        notification_type='TRADE',
        title='Trade Executed',
        message=f"Your SELL order for {trade_data['quantity']} shares of {trade_data['symbol']} was executed at ${trade_data['price']}.",
        data=trade_data
    )


def handle_announcement(db: Session, announcement_data: dict) -> None:
    """Handle system announcement event."""
    service = NotificationService(db)
    
    # Broadcast to all users (or specific user if user_id provided)
    if 'user_id' in announcement_data:
        service.create_notification(
            user_id=announcement_data['user_id'],
            notification_type='ANNOUNCEMENT',
            title=announcement_data['title'],
            message=announcement_data['message'],
            data=announcement_data
        )