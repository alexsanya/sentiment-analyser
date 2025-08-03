"""
Message handlers for RabbitMQ message processing system.

This package contains specialized handlers for different message types:
- tweet: Handles tweet message processing
- message_handler: Handles threaded RabbitMQ message processing for long-running operations
"""

from .tweet import handle_tweet_event
from .message_handler import create_threaded_message_handler, ThreadedMessageProcessor

# Alias for backward compatibility
create_message_handler = create_threaded_message_handler

__all__ = [
    "handle_tweet_event",
    "create_message_handler",
    "create_threaded_message_handler",
    "ThreadedMessageProcessor"
]