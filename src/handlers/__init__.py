"""
Message handlers for RabbitMQ message processing system.

This package contains specialized handlers for different message types:
- tweet: Handles tweet message processing
- message_handler: Handles RabbitMQ message processing with snipe action publishing
"""

from .tweet import handle_tweet_event
from .message_handler import create_message_handler

__all__ = [
    "handle_tweet_event",
    "create_message_handler"
]