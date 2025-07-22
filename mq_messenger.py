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
        password: Optional[str] = None
    ) -> None:
        """Initialize MQMessenger with connection parameters.
        
        Args:
            host: RabbitMQ server host
            port: RabbitMQ server port
            queue_name: Name of the queue to publish to
            username: Optional username for authentication
            password: Optional password for authentication
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
    
    @classmethod
    def from_env(cls) -> "MQMessenger":
        """Create MQMessenger instance from environment variables."""
        return cls(
            host=os.getenv("RABBITMQ_HOST", "localhost"),
            port=int(os.getenv("RABBITMQ_PORT", "5672")),
            queue_name=os.getenv("RABBITMQ_QUEUE", "tweet_events"),
            username=os.getenv("RABBITMQ_USERNAME"),
            password=os.getenv("RABBITMQ_PASSWORD")
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
        """
        try:
            self._ensure_connection()
            
            # Serialize message to JSON
            json_message = json.dumps(message, default=str)
            
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
                message_preview=str(message)[:100] + "..." if len(str(message)) > 100 else str(message)
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