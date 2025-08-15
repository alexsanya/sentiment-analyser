"""RabbitMQ subscriber service for consuming and publishing JSON messages."""

import json
import os
import time
import threading
from collections import deque
from typing import Dict, Any, Optional, List, Union, Callable, Type
import pika
from pika.adapters.blocking_connection import BlockingChannel
from pika.connection import Connection
from pika.spec import Basic, BasicProperties
from pydantic import ValidationError
from ..config.logging_config import get_logger
from .message_buffer import MessageBuffer
from ..models.schemas import TweetOutput, SnipeAction, TradeAction, NotifyAction

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
        # Consumer connection (dedicated for consuming only)
        self._consumer_connection: Optional[Connection] = None
        self._consumer_channel: Optional[BlockingChannel] = None
        
        # Publisher connection (for publishing and monitoring)
        self._publisher_connection: Optional[Connection] = None
        self._publisher_channel: Optional[BlockingChannel] = None
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
    
    def _create_connection_parameters(self) -> pika.ConnectionParameters:
        """Create connection parameters for RabbitMQ with optimized settings."""
        if self.username and self.password:
            credentials = pika.PlainCredentials(self.username, self.password)
            return pika.ConnectionParameters(
                host=self.host,
                port=self.port,
                credentials=credentials,
                heartbeat=300,  # 5 minutes heartbeat to prevent connection drops
                blocked_connection_timeout=300,  # 5 minutes blocked connection timeout
                connection_attempts=3,
                retry_delay=5.0,
                socket_timeout=10.0,
                tcp_options={"TCP_KEEPINTVL": 20, "TCP_KEEPCNT": 6}
            )
        else:
            return pika.ConnectionParameters(
                host=self.host, 
                port=self.port,
                heartbeat=300,  # 5 minutes heartbeat to prevent connection drops
                blocked_connection_timeout=300,  # 5 minutes blocked connection timeout
                connection_attempts=3,
                retry_delay=5.0,
                socket_timeout=10.0,
                tcp_options={"TCP_KEEPINTVL": 20, "TCP_KEEPCNT": 6}
            )
    
    def _create_consumer_connection(self) -> None:
        """Create dedicated connection for consuming messages."""
        try:
            parameters = self._create_connection_parameters()
            self._consumer_connection = pika.BlockingConnection(parameters)
            self._consumer_channel = self._consumer_connection.channel()
            
            # Declare consume queue as durable for persistence
            self._consumer_channel.queue_declare(queue=self.consume_queue, durable=True)
            
            logger.info("RabbitMQ consumer connection established", consume_queue=self.consume_queue)
            
        except Exception as e:
            logger.error(
                "Failed to create RabbitMQ consumer connection",
                error=str(e),
                host=self.host,
                port=self.port
            )
            self._cleanup_consumer_connection()
            raise
    
    def _create_publisher_connection(self) -> None:
        """Create dedicated connection for publishing messages."""
        try:
            parameters = self._create_connection_parameters()
            self._publisher_connection = pika.BlockingConnection(parameters)
            self._publisher_channel = self._publisher_connection.channel()
            
            # Declare publish queue as durable for persistence
            self._publisher_channel.queue_declare(queue=self.queue_name, durable=True)
            
            logger.info("RabbitMQ publisher connection established", queue_name=self.queue_name)
            
        except Exception as e:
            logger.error(
                "Failed to create RabbitMQ publisher connection",
                error=str(e),
                host=self.host,
                port=self.port
            )
            self._cleanup_publisher_connection()
            raise
    
    def _cleanup_consumer_connection(self) -> None:
        """Clean up consumer connection and channel resources."""
        if self._consumer_channel and not self._consumer_channel.is_closed:
            try:
                self._consumer_channel.close()
            except Exception as e:
                logger.warning("Error closing consumer channel", error=str(e))
        
        if self._consumer_connection and not self._consumer_connection.is_closed:
            try:
                self._consumer_connection.close()
            except Exception as e:
                logger.warning("Error closing consumer connection", error=str(e))
        
        self._consumer_channel = None
        self._consumer_connection = None
    
    def _cleanup_publisher_connection(self) -> None:
        """Clean up publisher connection and channel resources."""
        if self._publisher_channel and not self._publisher_channel.is_closed:
            try:
                self._publisher_channel.close()
            except Exception as e:
                logger.warning("Error closing publisher channel", error=str(e))
        
        if self._publisher_connection and not self._publisher_connection.is_closed:
            try:
                self._publisher_connection.close()
            except Exception as e:
                logger.warning("Error closing publisher connection", error=str(e))
        
        self._publisher_channel = None
        self._publisher_connection = None
    
    def _cleanup_connection(self) -> None:
        """Clean up all connection and channel resources."""
        self._cleanup_consumer_connection()
        self._cleanup_publisher_connection()
    
    def connect(self) -> None:
        """Establish connections to RabbitMQ server.
        
        Raises:
            Exception: If connections cannot be established
        """
        if not self.is_publisher_connected():
            self._create_publisher_connection()
            logger.info("RabbitMQ publisher connection established at startup")
    
    def test_connection(self) -> bool:
        """Test RabbitMQ publisher connection and return success status.
        
        Returns:
            bool: True if connection is successful, False otherwise
        """
        try:
            if not self.is_publisher_connected():
                self._create_publisher_connection()
            
            # Declare connection_events queue for test messages
            connection_events_queue = "connection_events"
            if self._publisher_channel is None:
                raise RuntimeError("Publisher channel is not available")
            
            self._publisher_channel.queue_declare(queue=connection_events_queue, durable=True)
            
            # Test publish a small message to validate connection
            test_message = {"_test": "connection_validation"}
            self._publisher_channel.basic_publish(
                exchange='',
                routing_key=connection_events_queue,
                body=json.dumps(test_message),
                properties=pika.BasicProperties(delivery_mode=2)
            )
            
            logger.info("RabbitMQ publisher connection test successful")
            return True
            
        except Exception as e:
            logger.error("RabbitMQ publisher connection test failed", error=str(e))
            return False
    
    def _ensure_publisher_connection(self) -> None:
        """Ensure publisher connection is active, create if needed."""
        if not self._publisher_connection or self._publisher_connection.is_closed:
            self._create_publisher_connection()
        elif not self._publisher_channel or self._publisher_channel.is_closed:
            self._publisher_channel = self._publisher_connection.channel()
            self._publisher_channel.queue_declare(queue=self.queue_name, durable=True)
    
    def _ensure_consumer_connection(self) -> None:
        """Ensure consumer connection is active, create if needed."""
        if not self._consumer_connection or self._consumer_connection.is_closed:
            self._create_consumer_connection()
        elif not self._consumer_channel or self._consumer_channel.is_closed:
            self._consumer_channel = self._consumer_connection.channel()
            self._consumer_channel.queue_declare(queue=self.consume_queue, durable=True)
    
    def publish(self, message: Union[Dict[str, Any], TweetOutput, SnipeAction, TradeAction, NotifyAction], queue_name: Optional[str] = None) -> bool:
        """Publish JSON message to RabbitMQ queue with automatic buffering on failure.
        
        Args:
            message: Dictionary, TweetOutput, SnipeAction, TradeAction, or NotifyAction object to be serialized as JSON and published
            queue_name: Optional queue name to publish to (defaults to self.queue_name)
            
        Returns:
            bool: True if message was published successfully, False otherwise
            
        Raises:
            ValueError: If message is invalid or too large
        """
        # Determine target queue
        target_queue = queue_name or self.queue_name
        
        # Input validation and type conversion
        if isinstance(message, (TweetOutput, SnipeAction, TradeAction, NotifyAction)):
            # Convert Pydantic model to dictionary
            message = message.model_dump()
        elif isinstance(message, dict):
            # Check for empty dictionary first
            if not message:
                raise ValueError("Message cannot be empty")
            
            # For dictionary messages, try to validate against known schemas
            # If no queue_name specified, assume TweetOutput for backward compatibility
            if not queue_name:
                try:
                    validated_message = TweetOutput(**message)
                    # Convert back to dict for JSON serialization
                    message = validated_message.model_dump()
                except ValidationError as e:
                    raise ValueError(f"Message does not match TweetOutput schema: {str(e)}")
        else:
            raise ValueError("Message must be a dictionary, TweetOutput, or SnipeAction object")
        
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
            self._ensure_publisher_connection()
            
            if self._publisher_channel is None:
                raise RuntimeError("Publisher channel is not available after connection check")
            
            # Declare target queue as durable for persistence (only if different from default)
            if target_queue != self.queue_name:
                self._publisher_channel.queue_declare(queue=target_queue, durable=True)
            
            # Publish message with persistence
            self._publisher_channel.basic_publish(
                exchange='',
                routing_key=target_queue,
                body=json_message,
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Make message persistent
                )
            )
            
            logger.info(
                "Message published to RabbitMQ",
                queue_name=target_queue,
                message_size=len(json_message)
            )
            return True
            
        except Exception as e:
            # Check for specific Pika buffer underflow error
            if "tx buffer size underflow" in str(e) or "AssertionError" in str(e):
                logger.error(
                    "Pika buffer underflow detected - this indicates a thread safety issue",
                    error=str(e),
                    queue_name=target_queue,
                    message_size=len(str(message)),
                    error_type="pika_buffer_underflow"
                )
                # Force reconnection on buffer underflow
                self._cleanup_publisher_connection()
            else:
                logger.error(
                    "Failed to publish message to RabbitMQ, attempting to buffer",
                    error=str(e),
                    queue_name=target_queue,
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
    
    def is_publisher_connected(self) -> bool:
        """Check if publisher connection is active.
        
        Returns:
            bool: True if publisher connection and channel are open, False otherwise
        """
        return (
            self._publisher_connection is not None and 
            not self._publisher_connection.is_closed and
            self._publisher_channel is not None and
            not self._publisher_channel.is_closed
        )
    
    def is_consumer_connected(self) -> bool:
        """Check if consumer connection is active.
        
        Returns:
            bool: True if consumer connection and channel are open, False otherwise
        """
        return (
            self._consumer_connection is not None and 
            not self._consumer_connection.is_closed and
            self._consumer_channel is not None and
            not self._consumer_channel.is_closed
        )
    
    def is_connected(self) -> bool:
        """Check if any connection is active (backwards compatibility).
        
        Returns:
            bool: True if publisher connection is active, False otherwise
        """
        return self.is_publisher_connected()
    
    def reconnect(self) -> bool:
        """Reconnect to RabbitMQ server by closing and re-establishing connections.
        
        Returns:
            bool: True if reconnection was successful, False otherwise
        """
        logger.info("Attempting to reconnect to RabbitMQ")
        
        # Remember if consumer was running before reconnection
        was_consuming = self.is_consuming()
        
        try:
            # Stop consuming first to clean up consumer thread
            if was_consuming:
                logger.info("Stopping consumer before reconnection")
                self.stop_consuming()
            
            # Clean up existing connections
            self._cleanup_connection()
            
            # Establish new publisher connection
            self._create_publisher_connection()
            
            # Verify the new connection works
            if not self.is_publisher_connected():
                logger.error("RabbitMQ reconnection failed - publisher connection not established")
                return False
            
            # Restart consumer if it was running before
            if was_consuming and self._message_handler:
                logger.info("Restarting consumer after successful reconnection")
                try:
                    self.start_consuming()
                    if self.is_consuming():
                        logger.info("Consumer successfully restarted after reconnection")
                    else:
                        logger.error("Failed to restart consumer after reconnection")
                        return False
                except Exception as e:
                    logger.error(
                        "Failed to restart consumer after reconnection",
                        error=str(e),
                        error_type=type(e).__name__
                    )
                    return False
            
            logger.info("RabbitMQ reconnection successful")
            return True
                
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
                self._ensure_publisher_connection()
                
                if self._publisher_channel is None:
                    raise RuntimeError("Publisher channel is not available after connection check")
                
                json_message = json.dumps(validated_dict, default=str)
                self._publisher_channel.basic_publish(
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
            
            # Ensure consumer connection is established
            self._ensure_consumer_connection()
            
            if self._consumer_channel is None:
                raise RuntimeError("Consumer channel is not available after connection check")
            
            # Declare the consume queue
            self._consumer_channel.queue_declare(queue=self.consume_queue, durable=True)
            
            # Set up consumer
            def wrapper_callback(channel: BlockingChannel, method: Basic.Deliver, properties: BasicProperties, body: bytes) -> None:
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
            self._consumer_tag = self._consumer_channel.basic_consume(
                queue=self.consume_queue,
                on_message_callback=wrapper_callback
            )
            
            logger.info("Message consumer started", consumer_tag=self._consumer_tag)
            
            # Keep consuming until stop signal
            consecutive_errors = 0
            max_consecutive_errors = 3
            error_backoff_delay = 1  # seconds
            
            while not self._stop_consuming.is_set():
                try:
                    if self._consumer_connection is None:
                        logger.error("Consumer connection lost during processing")
                        break
                    self._consumer_connection.process_data_events(time_limit=1)
                    # Reset error counter on successful processing
                    consecutive_errors = 0
                    
                except Exception as e:
                    if self._stop_consuming.is_set():
                        break
                    
                    consecutive_errors += 1
                    
                    # Check for specific Pika buffer underflow error
                    if "tx buffer size underflow" in str(e) or "AssertionError" in str(e):
                        logger.error(
                            "Pika buffer underflow detected in consumer - this indicates a thread safety issue",
                            error=str(e),
                            error_type="pika_buffer_underflow",
                            consecutive_errors=consecutive_errors
                        )
                        # Force reconnection on buffer underflow
                        self._cleanup_consumer_connection()
                        break
                    
                    # Handle recoverable connection errors with retry logic
                    elif consecutive_errors <= max_consecutive_errors:
                        logger.warning(
                            "Recoverable error in consumer, attempting retry",
                            error=str(e),
                            consecutive_errors=consecutive_errors,
                            max_consecutive_errors=max_consecutive_errors
                        )
                        
                        # Wait before retry (with backoff)
                        retry_delay = error_backoff_delay * consecutive_errors
                        if not self._stop_consuming.wait(timeout=retry_delay):
                            # Try to re-establish consumer connection
                            try:
                                self._cleanup_consumer_connection()
                                self._ensure_consumer_connection()
                                logger.info("Consumer connection re-established after error")
                                continue
                            except Exception as reconnect_error:
                                logger.error(
                                    "Failed to re-establish consumer connection",
                                    error=str(reconnect_error),
                                    consecutive_errors=consecutive_errors
                                )
                        else:
                            # Stop signal was set during wait
                            break
                    else:
                        # Too many consecutive errors, give up
                        logger.error(
                            "Too many consecutive errors in consumer, stopping consumption",
                            error=str(e),
                            consecutive_errors=consecutive_errors,
                            max_consecutive_errors=max_consecutive_errors
                        )
                        break
            
            logger.info("Message consumption stopped")
            
        except Exception as e:
            logger.error("Error in message consumption thread", error=str(e))
        finally:
            # Clean up consumer
            if self._consumer_tag and self._consumer_channel and not self._consumer_channel.is_closed:
                try:
                    self._consumer_channel.basic_cancel(self._consumer_tag)
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
    
    def __exit__(self, exc_type: Optional[Type[BaseException]], exc_val: Optional[BaseException], exc_tb: Optional[Any]) -> None:
        """Context manager exit."""
        self.close()