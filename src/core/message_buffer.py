"""Message buffer for storing messages when RabbitMQ is unavailable."""

import os
import time
import threading
from collections import deque
from typing import Dict, Any, List, Optional, cast
from ..config.logging_config import get_logger

logger = get_logger(__name__)


class MessageBuffer:
    """Thread-safe FIFO message buffer for storing messages during RabbitMQ outages."""
    
    def __init__(self, max_size: int = 10, enabled: bool = True) -> None:
        """Initialize message buffer with configurable capacity.
        
        Args:
            max_size: Maximum number of messages to store (default: 10)
            enabled: Whether buffering is enabled (default: True)
        """
        self.max_size = max_size
        self.enabled = enabled
        self._buffer: deque = deque(maxlen=max_size)
        self._lock = threading.Lock()
        
        logger.info(
            "MessageBuffer initialized",
            max_size=self.max_size,
            enabled=self.enabled
        )
    
    @classmethod
    def from_env(cls) -> "MessageBuffer":
        """Create MessageBuffer instance from environment variables.
        
        Environment variables:
            MESSAGE_BUFFER_ENABLED: Enable/disable buffering (default: "true")
            MESSAGE_BUFFER_SIZE: Maximum buffer size (default: "10")
        
        Returns:
            MessageBuffer instance configured from environment
        """
        enabled = os.getenv("MESSAGE_BUFFER_ENABLED", "true").lower() == "true"
        max_size = int(os.getenv("MESSAGE_BUFFER_SIZE", "10"))
        
        return cls(max_size=max_size, enabled=enabled)
    
    def add_message(self, message: Any) -> bool:
        """Add message to buffer with timestamp.
        
        When buffer is full, oldest message is automatically removed.
        Messages are stored with metadata including timestamp and size.
        
        Args:
            message: Dictionary message to buffer
            
        Returns:
            bool: True if message was added, False if buffering disabled
        """
        if not self.enabled:
            logger.debug("Message buffering disabled, skipping buffer")
            return False
        
        if not isinstance(message, dict):
            logger.warning("Invalid message type for buffer", message_type=type(message).__name__)
            return False
        
        with self._lock:
            # Check if buffer will overflow
            was_full = len(self._buffer) >= self.max_size
            
            # Create buffered message with metadata
            buffered_message = {
                "message": message,
                "timestamp": time.time(),
                "buffer_sequence": self._get_next_sequence()
            }
            
            # Add to buffer (automatically removes oldest if at max capacity)
            self._buffer.append(buffered_message)
            
            buffer_size = len(self._buffer)
            
            if was_full:
                logger.warning(
                    "Message buffer overflow, oldest message removed",
                    buffer_size=buffer_size,
                    max_size=self.max_size
                )
            else:
                logger.info(
                    "Message added to buffer",
                    buffer_size=buffer_size,
                    max_size=self.max_size
                )
        
        return True
    
    def get_pending_messages(self) -> List[Dict[str, Any]]:
        """Get all pending messages from buffer without removing them.
        
        Returns:
            List of buffered messages with metadata
        """
        with self._lock:
            return list(self._buffer)
    
    def pop_message(self) -> Optional[Dict[str, Any]]:
        """Remove and return oldest message from buffer.
        
        Returns:
            Oldest buffered message or None if buffer empty
        """
        with self._lock:
            if self._buffer:
                return cast(Dict[str, Any], self._buffer.popleft())
            return None
    
    def clear_buffer(self) -> int:
        """Clear all messages from buffer.
        
        Returns:
            Number of messages that were cleared
        """
        with self._lock:
            cleared_count = len(self._buffer)
            self._buffer.clear()
            
            if cleared_count > 0:
                logger.info("Message buffer cleared", cleared_messages=cleared_count)
            
            return cleared_count
    
    def is_full(self) -> bool:
        """Check if buffer is at maximum capacity.
        
        Returns:
            True if buffer is full, False otherwise
        """
        with self._lock:
            return len(self._buffer) >= self.max_size
    
    def size(self) -> int:
        """Get current number of messages in buffer.
        
        Returns:
            Current buffer size
        """
        with self._lock:
            return len(self._buffer)
    
    def is_empty(self) -> bool:
        """Check if buffer is empty.
        
        Returns:
            True if buffer is empty, False otherwise
        """
        with self._lock:
            return len(self._buffer) == 0
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive buffer status information.
        
        Returns:
            Dictionary with buffer status details
        """
        with self._lock:
            current_size = len(self._buffer)
            oldest_timestamp = None
            newest_timestamp = None
            
            if self._buffer:
                oldest_timestamp = self._buffer[0]["timestamp"]
                newest_timestamp = self._buffer[-1]["timestamp"]
            
            return {
                "enabled": self.enabled,
                "current_size": current_size,
                "max_size": self.max_size,
                "is_full": current_size >= self.max_size,
                "is_empty": current_size == 0,
                "oldest_message_timestamp": oldest_timestamp,
                "newest_message_timestamp": newest_timestamp,
                "oldest_message_age_seconds": time.time() - oldest_timestamp if oldest_timestamp else None
            }
    
    def _get_next_sequence(self) -> int:
        """Get next sequence number for message ordering.
        
        Returns:
            Monotonically increasing sequence number
        """
        if not hasattr(self, '_sequence_counter'):
            self._sequence_counter = 0
        
        self._sequence_counter += 1
        return self._sequence_counter
    
    def __len__(self) -> int:
        """Return current buffer size."""
        return self.size()
    
    def __bool__(self) -> bool:
        """Return True if buffer has messages."""
        return not self.is_empty()