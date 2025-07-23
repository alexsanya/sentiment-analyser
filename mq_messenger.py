"""RabbitMQ messenger service for publishing JSON messages."""

import json
import os
from typing import Dict, Any, Optional
import pika
from pika.adapters.blocking_connection import BlockingChannel
from pika.connection import Connection
from logging_config import get_logger

logger = get_logger(__name__)


class MQMessenger:
    """RabbitMQ messenger for publishing JSON messages with connection management."""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 5672,
        queue_name: str = "tweet_events",
        username: Optional[str] = None,
        password: Optional[str] = None,
        connect_on_init: bool = False
    ) -> None:
        """Initialize MQMessenger with connection parameters.
        
        Args:
            host: RabbitMQ server host
            port: RabbitMQ server port
            queue_name: Name of the queue to publish to
            username: Optional username for authentication
            password: Optional password for authentication
            connect_on_init: If True, establish connection immediately
        """
        self.host = host
        self.port = port
        self.queue_name = queue_name
        self.username = username
        self.password = password
        self._connection: Optional[Connection] = None
        self._channel: Optional[BlockingChannel] = None
        
        logger.info(
            "MQMessenger initialized",
            host=self.host,
            port=self.port,
            queue_name=self.queue_name,
            authenticated=bool(self.username)
        )
        
        if connect_on_init:
            self.connect()
    
    @classmethod
    def from_env(cls, connect_on_init: bool = False) -> "MQMessenger":
        """Create MQMessenger instance from environment variables."""
        return cls(
            host=os.getenv("RABBITMQ_HOST", "localhost"),
            port=int(os.getenv("RABBITMQ_PORT", "5672")),
            queue_name=os.getenv("RABBITMQ_QUEUE", "tweet_events"),
            username=os.getenv("RABBITMQ_USERNAME"),
            password=os.getenv("RABBITMQ_PASSWORD"),
            connect_on_init=connect_on_init
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
            
            # Test publish a small message to validate connection
            test_message = {"_test": "connection_validation"}
            self._channel.basic_publish(
                exchange='',
                routing_key=self.queue_name,
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
    
    def publish(self, message: Dict[str, Any]) -> bool:
        """Publish JSON message to RabbitMQ queue.
        
        Args:
            message: Dictionary to be serialized as JSON and published
            
        Returns:
            bool: True if message was published successfully, False otherwise
            
        Raises:
            ValueError: If message is invalid or too large
        """
        # Input validation
        if not isinstance(message, dict):
            raise ValueError("Message must be a dictionary")
        
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
                "Failed to publish message to RabbitMQ",
                error=str(e),
                queue_name=self.queue_name,
                message_size=len(str(message))
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
    
    def close(self) -> None:
        """Close connection and clean up resources."""
        logger.info("Closing MQMessenger connection")
        self._cleanup_connection()
    
    def __enter__(self) -> "MQMessenger":
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()