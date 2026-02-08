"""
Notification Schemas for API Request/Response
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class NotificationBase(BaseModel):
    """Base notification schema."""
    type: str = Field(..., description="Notification type: ORDER, TRADE, ANNOUNCEMENT, POSITION")
    title: str = Field(..., max_length=128)
    message: str


class NotificationCreate(NotificationBase):
    """Schema for creating a notification."""
    user_id: int
    data: Optional[dict] = None


class NotificationResponse(NotificationBase):
    """Schema for notification response."""
    id: int
    user_id: int
    data: Optional[str] = None
    is_read: bool
    created_at: datetime
    read_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    """Schema for list of notifications."""
    total: int
    unread_count: int
    notifications: list[NotificationResponse]


class MarkReadRequest(BaseModel):
    """Schema for marking notification as read."""
    notification_id: int


class AnnouncementRequest(BaseModel):
    """Schema for creating an announcement."""
    title: str = Field(..., max_length=128)
    message: str
    user_id: Optional[int] = None  # If None, broadcast to all users