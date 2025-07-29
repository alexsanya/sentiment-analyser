"""
Message handlers for RabbitMQ message processing system.

This package contains specialized handlers for different message types:
- tweet: Handles tweet message processing
"""

from .tweet import handle_tweet_event

__all__ = [
    "handle_tweet_event"
]