import os
import signal
from typing import Any
from dotenv import load_dotenv
from logging_config import setup_logging, get_logger
from websocket_manager import WebSocketManager
from mq_messenger import MQMessenger
from handlers import (
    on_error,
    on_close,
    on_open
)

# Initialize module-level logger
setup_logging()  # Auto-detects environment
logger = get_logger(__name__)

# Removed global MQMessenger instance - now using dependency injection


def initialize_rabbitmq() -> MQMessenger:
    """Initialize and test RabbitMQ connection at startup.
    
    Returns:
        MQMessenger: Successfully connected and validated MQMessenger instance
        
    Raises:
        SystemExit: If RabbitMQ connection cannot be established or validated
    """
    try:
        logger.info("Initializing RabbitMQ connection...")
        messenger = MQMessenger.from_env(connect_on_init=True)
        
        # Test the connection
        if not messenger.test_connection():
            logger.error("RabbitMQ connection test failed - shutting down")
            raise Exception("RabbitMQ connection validation failed")
        
        logger.info("RabbitMQ connection validated successfully")
        return messenger
        
    except Exception as e:
        logger.error(
            "Failed to establish RabbitMQ connection at startup",
            error=str(e)
        )
        raise SystemExit(1)




# Message handling is now integrated into WebSocketManager class


# Main function
def main(x_api_key: str) -> None:
    environment = os.getenv("ENVIRONMENT", "development")
    logger.info("Starting news-powered trading system", environment=environment)
    
    # Initialize and test RabbitMQ connection at startup
    mq_messenger = initialize_rabbitmq()
    
    # Create WebSocket manager with callback functions and MQ messenger
    ws_manager = WebSocketManager(None, on_error, on_close, on_open, mq_messenger)
    
    # Register signal handler for graceful shutdown using the manager
    def shutdown_handler(signum: int, frame: Any) -> None:
        logger.info("Shutdown signal received, cleaning up...")
        ws_manager._signal_handler(signum, frame)
        if mq_messenger:
            mq_messenger.close()
    
    signal.signal(signal.SIGINT, shutdown_handler)
    logger.info("Signal handler registered for graceful shutdown")
    
    url = "wss://ws.twitterapi.io/twitter/tweet/websocket"
    headers = {"x-api-key": x_api_key}
    
    logger.info("Connecting to Twitter.io WebSocket", url=url)
    ws_manager.connect(url, headers)
    
    logger.info("Application shutting down")
    if mq_messenger:
        mq_messenger.close()

if __name__ == "__main__":
    load_dotenv()
    main(os.environ["TWITTERAPI_KEY"])
