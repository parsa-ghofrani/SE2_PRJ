"""
Message Broker Client for Publishing/Consuming Events
Using Redis Pub/Sub for simplicity
"""
import json
import redis
from typing import Any, Callable
from app.core.config import settings


class MessageBroker:
    """Redis-based message broker for asynchronous communication."""
    
    def __init__(self):
        self.redis_client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=0,
            decode_responses=True
        )
        self.pubsub = self.redis_client.pubsub()
    
    def publish(self, channel: str, message: dict[str, Any]) -> None:
        """
        Publish a message to a channel.
        
        Args:
            channel: Channel name (e.g., 'orders', 'trades', 'announcements')
            message: Message data as dictionary
        """
        self.redis_client.publish(channel, json.dumps(message))
    
    def subscribe(self, channel: str, callback: Callable[[dict], None]) -> None:
        """
        Subscribe to a channel and process messages.
        
        Args:
            channel: Channel name to subscribe to
            callback: Function to call when message received
        """
        self.pubsub.subscribe(channel)
        
        for message in self.pubsub.listen():
            if message['type'] == 'message':
                data = json.loads(message['data'])
                callback(data)
    
    def close(self):
        """Close the connection."""
        self.pubsub.close()
        self.redis_client.close()


# Global instance
message_broker = MessageBroker()