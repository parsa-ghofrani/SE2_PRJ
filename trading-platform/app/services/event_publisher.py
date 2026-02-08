"""
Event Publisher
Publishes events to message broker when things happen
"""
from app.core.message_broker import message_broker


class EventPublisher:
    """Publishes events to message broker."""
    
    @staticmethod
    def publish_order_created(order_data: dict) -> None:
        """Publish order created event."""
        message_broker.publish('orders', {
            'event': 'order_created',
            'data': order_data
        })
    
    @staticmethod
    def publish_trade_executed(trade_data: dict) -> None:
        """Publish trade executed event."""
        message_broker.publish('trades', {
            'event': 'trade_executed',
            'data': trade_data
        })
    
    @staticmethod
    def publish_announcement(announcement_data: dict) -> None:
        """Publish announcement event."""
        message_broker.publish('announcements', {
            'event': 'announcement',
            'data': announcement_data
        })