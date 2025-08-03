"""
Main application entry point with threaded message processing.

This version uses the threaded message handler pattern from Pika examples
to handle potentially long-running sentiment analysis operations in separate
threads while maintaining message consumption throughput.
"""

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
from src.handlers import create_threaded_message_handler

# Initialize module-level logger
setup_logging()  # Auto-detects environment
logger = get_logger(__name__)

# Global shutdown flag and processor reference
shutdown_requested = False
message_processor: Optional[Any] = None


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
    """Main application entry point with threaded message processing."""
    global shutdown_requested, message_processor
    
    environment = os.getenv("ENVIRONMENT", "development")
    logger.info("Starting threaded RabbitMQ message processor", environment=environment)
    
    # Initialize and test RabbitMQ connection at startup
    mq_subscriber = initialize_rabbitmq()
    
    # Initialize RabbitMQ connection monitor
    connection_monitor: Optional[RabbitMQConnectionMonitor] = initialize_rabbitmq_monitor(mq_subscriber)
    
    # Register signal handler for graceful shutdown
    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)
    logger.info("Signal handlers registered for graceful shutdown")
    
    try:
        # Create threaded message processor
        message_processor = create_threaded_message_handler(mq_subscriber)
        
        # Start threaded message processing
        message_processor.start_processing()
        
        # Configure basic QOS for the consumer channel to limit unacknowledged messages
        # This prevents overwhelming the system with too many concurrent threads
        if mq_subscriber._consumer_channel:
            mq_subscriber._consumer_channel.basic_qos(prefetch_count=10)
            logger.info("Consumer QoS configured - max 10 unacknowledged messages")
        
        logger.info("Threaded message processing started. Press Ctrl+C to shutdown.")
        
        # Main loop - monitor status and handle shutdown
        status_log_interval = 60  # Log status every 60 seconds
        last_status_log = 0
        
        while not shutdown_requested:
            current_time = time.time()
            
            # Periodically log processor status
            if current_time - last_status_log >= status_log_interval:
                status = message_processor.get_status()
                logger.info(
                    "Threaded processor status",
                    **status
                )
                last_status_log = current_time
            
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
        shutdown_requested = True
    
    finally:
        logger.info("Application shutting down")
        
        # Cleanup resources in proper order
        if message_processor:
            logger.info("Stopping threaded message processor...")
            # Give threads reasonable time to complete processing
            message_processor.stop_processing(timeout=30.0)
        
        if connection_monitor:
            logger.info("Stopping connection monitor...")
            connection_monitor.stop()
        
        if mq_subscriber:
            logger.info("Closing MQ subscriber...")
            mq_subscriber.close()
        
        logger.info("Application shutdown complete")


if __name__ == "__main__":
    load_dotenv()
    # Initialize Logfire observability
    initialize_logfire()
    main()