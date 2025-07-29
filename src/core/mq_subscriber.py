"""RabbitMQ subscriber service for consuming and publishing JSON messages."""

import json
import os
import time
import threading
from collections import deque
from typing import Dict, Any, Optional, List, Union, Callable
import pika
from pika.adapters.blocking_connection import BlockingChannel
from pika.connection import Connection
from pydantic import ValidationError
from ..config.logging_config import get_logger
from .message_buffer import MessageBuffer
from ..models.schemas import TweetOutput

logger = get_logger(__name__)


class MQSubscriber:
    """RabbitMQ subscriber for consuming and publishing JSON messages with connection management."""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 5672,
        queue_name: str = "tweet_events",
        username: Optional[str] = None,
        password: Optional[str] = None,
        connect_on_init: bool = False,
        message_buffer: Optional[MessageBuffer] = None,
        consume_queue: Optional[str] = None
    ) -> None:
        """Initialize MQSubscriber with connection parameters.
        
        Args:
            host: RabbitMQ server host
            port: RabbitMQ server port
            queue_name: Name of the queue to publish to
            username: Optional username for authentication
            password: Optional password for authentication
            connect_on_init: If True, establish connection immediately
            message_buffer: Optional MessageBuffer instance for storing messages during outages
            consume_queue: Optional queue name to consume from (defaults to queue_name)
        """
        self.host = host
        self.port = port
        self.queue_name = queue_name
        self.consume_queue = consume_queue or queue_name
        self.username = username
        self.password = password
        self._connection: Optional[Connection] = None
        self._channel: Optional[BlockingChannel] = None
        self.message_buffer = message_buffer if message_buffer is not None else MessageBuffer.from_env()
        
        # Consumer-related attributes
        self._consumer_thread: Optional[threading.Thread] = None
        self._consumer_tag: Optional[str] = None
        self._stop_consuming = threading.Event()
        self._message_handler: Optional[Callable] = None
        
        logger.info(
            "MQSubscriber initialized",
            host=self.host,
            port=self.port,
            queue_name=self.queue_name,
            consume_queue=self.consume_queue,
            authenticated=bool(self.username),
            buffer_enabled=self.message_buffer.enabled,
            buffer_size=self.message_buffer.max_size
        )
        
        if connect_on_init:
            self.connect()
    
    @classmethod
    def from_env(cls, connect_on_init: bool = False) -> "MQSubscriber":
        """Create MQSubscriber instance from environment variables."""
        return cls(
            host=os.getenv("RABBITMQ_HOST", "localhost"),
            port=int(os.getenv("RABBITMQ_PORT", "5672")),
            queue_name=os.getenv("RABBITMQ_QUEUE", "tweet_events"),
            username=os.getenv("RABBITMQ_USERNAME"),
            password=os.getenv("RABBITMQ_PASSWORD"),
            connect_on_init=connect_on_init,
            consume_queue=os.getenv("RABBITMQ_CONSUME_QUEUE")
        )
    
    def _create_connection(self) -> None:
        """Create connection to RabbitMQ server."""
        try:
            if self.username and self.password:
                credentials = pika.PlainCredentials(self.username, self.password)
                parameters = pika.ConnectionParameters(
                    host=self.host,
                    port=self.port,
                    credentials=credentials
                )
            else:
                parameters = pika.ConnectionParameters(host=self.host, port=self.port)
            
            self._connection = pika.BlockingConnection(parameters)
            self._channel = self._connection.channel()
            
            # Declare queue as durable for persistence
            self._channel.queue_declare(queue=self.queue_name, durable=True)
            
            logger.info("RabbitMQ connection established", queue_name=self.queue_name)
            
        except Exception as e:
            logger.error(
                "Failed to create RabbitMQ connection",
                error=str(e),
                host=self.host,
                port=self.port
            )
            self._cleanup_connection()
            raise
    
    def _cleanup_connection(self) -> None:
        """Clean up connection and channel resources."""
        if self._channel and not self._channel.is_closed:
            try:
                self._channel.close()
            except Exception as e:
                logger.warning("Error closing channel", error=str(e))
        
        if self._connection and not self._connection.is_closed:
            try:
                self._connection.close()
            except Exception as e:
                logger.warning("Error closing connection", error=str(e))
        
        self._channel = None
        self._connection = None
    
    def connect(self) -> None:
        """Establish connection to RabbitMQ server.
        
        Raises:
            Exception: If connection cannot be established
        """
        if not self.is_connected():
            self._create_connection()
            logger.info("RabbitMQ connection established at startup")
    
    def test_connection(self) -> bool:
        """Test RabbitMQ connection and return success status.
        
        Returns:
            bool: True if connection is successful, False otherwise
        """
        try:
            if not self.is_connected():
                self._create_connection()
            
            # Declare connection_events queue for test messages
            connection_events_queue = "connection_events"
            self._channel.queue_declare(queue=connection_events_queue, durable=True)
            
            # Test publish a small message to validate connection
            test_message = {"_test": "connection_validation"}
            self._channel.basic_publish(
                exchange='',
                routing_key=connection_events_queue,
                body=json.dumps(test_message),
                properties=pika.BasicProperties(delivery_mode=2)
            )
            
            logger.info("RabbitMQ connection test successful")
            return True
            
        except Exception as e:
            logger.error("RabbitMQ connection test failed", error=str(e))
            return False
    
    def _ensure_connection(self) -> None:
        """Ensure connection is active, create if needed."""
        if not self._connection or self._connection.is_closed:
            self._create_connection()
        elif not self._channel or self._channel.is_closed:
            self._channel = self._connection.channel()
            self._channel.queue_declare(queue=self.queue_name, durable=True)
    
    def publish(self, message: Union[Dict[str, Any], TweetOutput]) -> bool:
        """Publish JSON message to RabbitMQ queue with automatic buffering on failure.
        
        Args:
            message: Dictionary or TweetOutput object to be serialized as JSON and published
            
        Returns:
            bool: True if message was published successfully, False otherwise
            
        Raises:
            ValueError: If message is invalid or too large
        """
        # Input validation and type conversion
        if isinstance(message, TweetOutput):
            # Convert TweetOutput to dictionary
            message = message.model_dump()
        elif isinstance(message, dict):
            # Check for empty dictionary first
            if not message:
                raise ValueError("Message cannot be empty")
            
            # Validate dictionary against TweetOutput schema
            try:
                validated_message = TweetOutput(**message)
                # Convert back to dict for JSON serialization
                message = validated_message.model_dump()
            except ValidationError as e:
                raise ValueError(f"Message does not match expected schema: {str(e)}")
        else:
            raise ValueError("Message must be a dictionary or TweetOutput object")
        
        # Final check for empty message after processing
        if not message:
            raise ValueError("Message cannot be empty")
        
        # Pre-validate message size by serializing to JSON
        try:
            json_message = json.dumps(message, default=str)
        except (TypeError, ValueError) as e:
            raise ValueError(f"Message cannot be serialized to JSON: {str(e)}")
        
        # Check message size (RabbitMQ default max is 128MB, we'll limit to 1MB for safety)
        max_message_size = 1024 * 1024  # 1MB
        message_size = len(json_message.encode('utf-8'))
        if message_size > max_message_size:
            raise ValueError(f"Message too large: {message_size} bytes exceeds {max_message_size} bytes")
        
        try:
            self._ensure_connection()
            
            # Publish message with persistence
            self._channel.basic_publish(
                exchange='',
                routing_key=self.queue_name,
                body=json_message,
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Make message persistent
                )
            )
            
            logger.info(
                "Message published to RabbitMQ",
                queue_name=self.queue_name,
                message_size=len(json_message)
            )
            return True
            
        except Exception as e:
            logger.error(
                "Failed to publish message to RabbitMQ, attempting to buffer",
                error=str(e),
                queue_name=self.queue_name,
                message_size=len(str(message))
            )
            
            # Try to buffer the message
            if self.message_buffer.add_message(message):
                logger.info(
                    "Message buffered due to RabbitMQ failure",
                    buffer_size=self.message_buffer.size(),
                    max_buffer_size=self.message_buffer.max_size
                )
            else:
                logger.warning(
                    "Failed to buffer message - buffering disabled or message invalid",
                    buffer_enabled=self.message_buffer.enabled
                )
            
            return False
    
    def is_connected(self) -> bool:
        """Check if connection is active.
        
        Returns:
            bool: True if connection and channel are open, False otherwise
        """
        return (
            self._connection is not None and 
            not self._connection.is_closed and
            self._channel is not None and
            not self._channel.is_closed
        )
    
    def reconnect(self) -> bool:
        """Reconnect to RabbitMQ server by closing and re-establishing connection.
        
        Returns:
            bool: True if reconnection was successful, False otherwise
        """
        logger.info("Attempting to reconnect to RabbitMQ")
        
        try:
            # Clean up existing connection
            self._cleanup_connection()
            
            # Establish new connection
            self._create_connection()
            
            # Verify the new connection works
            if self.is_connected():
                logger.info("RabbitMQ reconnection successful")
                return True
            else:
                logger.error("RabbitMQ reconnection failed - connection not established")
                return False
                
        except Exception as e:
            logger.error(
                "RabbitMQ reconnection failed",
                error=str(e),
                error_type=type(e).__name__
            )
            return False
    
    def flush_buffer(self) -> int:
        """Flush all buffered messages to RabbitMQ.
        
        Attempts to publish all buffered messages in FIFO order.
        Successfully published messages are removed from buffer.
        If any message fails, remaining messages stay in buffer.
        
        Returns:
            int: Number of messages successfully flushed
        """
        if self.message_buffer.is_empty():
            logger.debug("No messages in buffer to flush")
            return 0
        
        flushed_count = 0
        initial_buffer_size = self.message_buffer.size()
        
        logger.info(
            "Starting buffer flush",
            buffer_size=initial_buffer_size
        )
        
        # Process messages in FIFO order
        while not self.message_buffer.is_empty():
            buffered_message = self.message_buffer.pop_message()
            if not buffered_message:
                break
            
            original_message = buffered_message["message"]
            buffer_timestamp = buffered_message["timestamp"]
            
            try:
                # Validate message against schema before publishing
                try:
                    validated_message = TweetOutput(**original_message)
                    validated_dict = validated_message.model_dump()
                except ValidationError as e:
                    logger.warning(
                        "Skipping buffered message due to schema validation failure",
                        error=str(e),
                        buffer_age_seconds=round(time.time() - buffer_timestamp, 2)
                    )
                    continue
                
                # Try to publish the validated message directly (bypassing buffer logic)
                self._ensure_connection()
                
                json_message = json.dumps(validated_dict, default=str)
                self._channel.basic_publish(
                    exchange='',
                    routing_key=self.queue_name,
                    body=json_message,
                    properties=pika.BasicProperties(delivery_mode=2)
                )
                
                flushed_count += 1
                logger.info(
                    "Buffered message flushed to RabbitMQ",
                    flushed_count=flushed_count,
                    buffer_age_seconds=round(time.time() - buffer_timestamp, 2)
                )
                
            except Exception as e:
                # Re-add message to front of buffer and stop flushing
                # Using a temporary deque to preserve order
                temp_buffer = deque([buffered_message])
                temp_buffer.extend(self.message_buffer._buffer)
                
                with self.message_buffer._lock:
                    self.message_buffer._buffer.clear()
                    self.message_buffer._buffer.extend(temp_buffer)
                
                logger.error(
                    "Failed to flush buffered message, stopping flush operation",
                    error=str(e),
                    flushed_count=flushed_count,
                    remaining_in_buffer=self.message_buffer.size()
                )
                break
        
        logger.info(
            "Buffer flush completed",
            flushed_count=flushed_count,
            initial_buffer_size=initial_buffer_size,
            remaining_in_buffer=self.message_buffer.size()
        )
        
        return flushed_count
    
    def get_buffer_status(self) -> Dict[str, Any]:
        """Get current message buffer status.
        
        Returns:
            Dictionary with comprehensive buffer status information
        """
        return self.message_buffer.get_status()
    
    def set_message_handler(self, handler: Callable) -> None:
        """Set the message handler for consuming messages.
        
        Args:
            handler: Callback function with signature (channel, method, properties, body)
        """
        self._message_handler = handler
        logger.info("Message handler set for consumption")
    
    def _consume_messages(self) -> None:
        """Internal method to consume messages in a separate thread."""
        try:
            logger.info("Starting message consumption", consume_queue=self.consume_queue)
            
            # Ensure connection is established
            self._ensure_connection()
            
            # Declare the consume queue
            self._channel.queue_declare(queue=self.consume_queue, durable=True)
            
            # Set up consumer
            def wrapper_callback(channel, method, properties, body):
                if not self._stop_consuming.is_set() and self._message_handler:
                    try:
                        self._message_handler(channel, method, properties, body)
                    except Exception as e:
                        logger.error(
                            "Error in message handler",
                            error=str(e),
                            routing_key=method.routing_key
                        )
                        # Reject the message to avoid infinite loops
                        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            
            # Start consuming
            self._consumer_tag = self._channel.basic_consume(
                queue=self.consume_queue,
                on_message_callback=wrapper_callback
            )
            
            logger.info("Message consumer started", consumer_tag=self._consumer_tag)
            
            # Keep consuming until stop signal
            while not self._stop_consuming.is_set():
                try:
                    self._connection.process_data_events(time_limit=1)
                except Exception as e:
                    if not self._stop_consuming.is_set():
                        logger.error("Error processing data events", error=str(e))
                        break
            
            logger.info("Message consumption stopped")
            
        except Exception as e:
            logger.error("Error in message consumption thread", error=str(e))
        finally:
            # Clean up consumer
            if self._consumer_tag and self._channel and not self._channel.is_closed:
                try:
                    self._channel.basic_cancel(self._consumer_tag)
                    logger.info("Consumer cancelled", consumer_tag=self._consumer_tag)
                except Exception as e:
                    logger.warning("Error cancelling consumer", error=str(e))
            self._consumer_tag = None
    
    def start_consuming(self) -> None:
        """Start consuming messages in a separate thread.
        
        Requires a message handler to be set via set_message_handler().
        """
        if not self._message_handler:
            raise ValueError("Message handler must be set before starting consumption")
        
        if self._consumer_thread and self._consumer_thread.is_alive():
            logger.warning("Consumer thread is already running")
            return
        
        self._stop_consuming.clear()
        self._consumer_thread = threading.Thread(target=self._consume_messages, daemon=True)
        self._consumer_thread.start()
        
        logger.info("Consumer thread started")
    
    def stop_consuming(self) -> None:
        """Stop consuming messages and wait for consumer thread to finish."""
        if not self._consumer_thread or not self._consumer_thread.is_alive():
            logger.info("Consumer thread is not running")
            return
        
        logger.info("Stopping message consumption...")
        self._stop_consuming.set()
        
        # Wait for consumer thread to finish
        if self._consumer_thread:
            self._consumer_thread.join(timeout=5)
            if self._consumer_thread.is_alive():
                logger.warning("Consumer thread did not stop within timeout")
            else:
                logger.info("Consumer thread stopped successfully")
        
        self._consumer_thread = None
    
    def is_consuming(self) -> bool:
        """Check if currently consuming messages.
        
        Returns:
            bool: True if consumer thread is active, False otherwise
        """
        return (
            self._consumer_thread is not None and 
            self._consumer_thread.is_alive() and 
            not self._stop_consuming.is_set()
        )
    
    def close(self) -> None:
        """Close connection and clean up resources."""
        logger.info("Closing MQSubscriber connection")
        
        # Stop consuming first
        self.stop_consuming()
        
        # Then cleanup connection
        self._cleanup_connection()
    
    def __enter__(self) -> "MQSubscriber":
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()