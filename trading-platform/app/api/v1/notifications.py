"""
Notification API Endpoints
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.services.notification_service import NotificationService
from app.services.event_publisher import EventPublisher
from app.schemas.notification import (
    NotificationResponse,
    NotificationListResponse,
    NotificationCreate,
    MarkReadRequest,
    AnnouncementRequest,
)

router = APIRouter()


@router.get("/", response_model=NotificationListResponse)
def get_notifications(
    user_id: int = Query(..., description="User ID to get notifications for"),
    unread_only: bool = Query(False, description="Only return unread notifications"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of records"),
    db: Session = Depends(get_db),
):
    """
    Get notifications for a user.
    
    - **user_id**: User ID
    - **unread_only**: Filter for unread notifications only
    - **skip**: Pagination offset
    - **limit**: Maximum results per page
    """
    service = NotificationService(db)
    
    notifications = service.get_user_notifications(
        user_id=user_id,
        unread_only=unread_only,
        skip=skip,
        limit=limit,
    )
    
    # Get counts
    unread_count = service.get_unread_count(user_id)
    
    # Get total (just use a large query for simplicity)
    total_notifications = service.get_user_notifications(user_id, skip=0, limit=10000)
    
    return NotificationListResponse(
        total=len(total_notifications),
        unread_count=unread_count,
        notifications=notifications,
    )


@router.get("/unread-count")
def get_unread_count(
    user_id: int = Query(..., description="User ID"),
    db: Session = Depends(get_db),
):
    """
    Get count of unread notifications for a user.
    
    - **user_id**: User ID
    """
    service = NotificationService(db)
    count = service.get_unread_count(user_id)
    
    return {"user_id": user_id, "unread_count": count}


@router.post("/", response_model=NotificationResponse, status_code=201)
def create_notification(
    notification: NotificationCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new notification.
    
    - **user_id**: User ID to notify
    - **type**: Notification type (ORDER, TRADE, ANNOUNCEMENT, POSITION)
    - **title**: Notification title
    - **message**: Notification message
    - **data**: Optional JSON data
    """
    service = NotificationService(db)
    
    created = service.create_notification(
        user_id=notification.user_id,
        notification_type=notification.type,
        title=notification.title,
        message=notification.message,
        data=notification.data,
    )
    
    return created


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
def mark_as_read(
    notification_id: int,
    user_id: int = Query(..., description="User ID for security verification"),
    db: Session = Depends(get_db),
):
    """
    Mark a notification as read.
    
    - **notification_id**: ID of the notification
    - **user_id**: User ID (must match notification owner)
    """
    service = NotificationService(db)
    
    notification = service.mark_as_read(notification_id, user_id)
    
    if not notification:
        raise HTTPException(
            status_code=404,
            detail="Notification not found or you don't have permission",
        )
    
    return notification


@router.post("/mark-all-read")
def mark_all_as_read(
    user_id: int = Query(..., description="User ID"),
    db: Session = Depends(get_db),
):
    """
    Mark all notifications as read for a user.
    
    - **user_id**: User ID
    """
    service = NotificationService(db)
    count = service.mark_all_as_read(user_id)
    
    return {"user_id": user_id, "marked_read": count}


@router.delete("/{notification_id}")
def delete_notification(
    notification_id: int,
    user_id: int = Query(..., description="User ID for security verification"),
    db: Session = Depends(get_db),
):
    """
    Delete a notification.
    
    - **notification_id**: ID of the notification
    - **user_id**: User ID (must match notification owner)
    """
    service = NotificationService(db)
    
    deleted = service.delete_notification(notification_id, user_id)
    
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Notification not found or you don't have permission",
        )
    
    return {"message": "Notification deleted successfully"}


@router.post("/announcements", status_code=201)
def create_announcement(
    announcement: AnnouncementRequest,
    db: Session = Depends(get_db),
):
    """
    Create an announcement (admin endpoint).
    
    - **title**: Announcement title
    - **message**: Announcement message
    - **user_id**: Optional - if provided, send to specific user, otherwise broadcast
    """
    # Publish announcement event
    EventPublisher.publish_announcement({
        'title': announcement.title,
        'message': announcement.message,
        'user_id': announcement.user_id,
    })
    
    # If specific user, create notification directly
    if announcement.user_id:
        service = NotificationService(db)
        service.create_notification(
            user_id=announcement.user_id,
            notification_type='ANNOUNCEMENT',
            title=announcement.title,
            message=announcement.message,
        )
    
    return {
        "message": "Announcement published",
        "broadcast": announcement.user_id is None,
    }