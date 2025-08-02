import json
import os
import signal
import time
from typing import Any, Optional
from dotenv import load_dotenv
from src.config.logging_config import setup_logging, get_logger
from src.config.logfire_config import initialize_logfire
from src.core.mq_subscriber import MQSubscriber
from src.core.rabbitmq_monitor import RabbitMQConnectionMonitor
from src.handlers import create_message_handler

# Initialize module-level logger
setup_logging()  # Auto-detects environment
logger = get_logger(__name__)
# Global shutdown flag
shutdown_requested = False


def initialize_rabbitmq() -> MQSubscriber:
    """Initialize and test RabbitMQ connection at startup.
    
    Returns:
        MQSubscriber: Successfully connected and validated MQSubscriber instance
        
    Raises:
        SystemExit: If RabbitMQ connection cannot be established or validated
    """
    try:
        logger.info("Initializing RabbitMQ connection...")
        subscriber = MQSubscriber.from_env(connect_on_init=True)
        
        # Test the connection
        if not subscriber.test_connection():
            logger.error("RabbitMQ connection test failed - shutting down")
            raise Exception("RabbitMQ connection validation failed")
        
        logger.info("RabbitMQ connection validated successfully")
        return subscriber
        
    except Exception as e:
        logger.error(
            "Failed to establish RabbitMQ connection at startup",
            error=str(e)
        )
        raise SystemExit(1)

def initialize_rabbitmq_monitor(mq_subscriber: MQSubscriber) -> Optional[RabbitMQConnectionMonitor]:
    """Initialize RabbitMQ connection monitor if enabled."""
    if os.getenv("RABBITMQ_MONITOR_ENABLED", "true").lower() == "true":
        connection_monitor = RabbitMQConnectionMonitor.from_env(mq_subscriber)
        connection_monitor.start()
        logger.info("RabbitMQ connection monitoring enabled")
        return connection_monitor
    else:
        logger.info("RabbitMQ connection monitoring disabled")
        return None


def shutdown_handler(signum: int, frame: Any) -> None:
    """Handle shutdown signals gracefully."""
    global shutdown_requested
    logger.info("Shutdown signal received, cleaning up...")
    shutdown_requested = True

def main() -> None:
    """Main application entry point."""
    global shutdown_requested
    
    environment = os.getenv("ENVIRONMENT", "development")
    logger.info("Starting RabbitMQ message processor", environment=environment)
    
    # Initialize and test RabbitMQ connection at startup
    mq_subscriber = initialize_rabbitmq()
    
    # Initialize RabbitMQ connection monitor
    connection_monitor: Optional[RabbitMQConnectionMonitor] = initialize_rabbitmq_monitor(mq_subscriber)
    
    # Register signal handler for graceful shutdown
    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)
    logger.info("Signal handlers registered for graceful shutdown")
    
    try:
        # Create message handler with MQSubscriber dependency injected
        handler = create_message_handler(mq_subscriber)
        
        # Set up message handler and start consuming
        mq_subscriber.set_message_handler(handler)
        mq_subscriber.start_consuming()
        
        logger.info("Application started and consuming messages. Press Ctrl+C to shutdown.")
        
        while not shutdown_requested:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
        shutdown_requested = True
    
    finally:
        logger.info("Application shutting down")
        
        # Cleanup resources
        if connection_monitor:
            connection_monitor.stop()
        if mq_subscriber:
            mq_subscriber.close()

if __name__ == "__main__":
    load_dotenv()
    # Initialize Logfire observability
    initialize_logfire()
    main()
