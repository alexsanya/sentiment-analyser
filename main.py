import traceback
import websocket
import json
import os
import signal
from functools import partial
from dotenv import load_dotenv
from logging_config import setup_logging, get_logger
from websocket_manager import WebSocketManager
from mq_messenger import MQMessenger
from handlers import (
    handle_connected_event,
    handle_ping_event,
    handle_tweet_event,
    handle_unknown_event,
    on_error,
    on_close,
    on_open
)

# Initialize module-level logger
setup_logging()  # Auto-detects environment
logger = get_logger(__name__)

# Global MQMessenger instance
mq_messenger: MQMessenger = None




# Message handling callback
def on_message(ws: websocket.WebSocketApp, message: str) -> None:
    """Main message dispatcher that routes to appropriate handlers based on event type."""
    try:
        logger.info("Message received", message_preview=message[:100] + "..." if len(message) > 100 else message)
        # Convert to JSON
        result_json = json.loads(message)
        event_type = result_json.get("event_type")
        
        # Route to appropriate handler based on event type
        if event_type == "connected":
            handle_connected_event(result_json)
        elif event_type == "ping":
            handle_ping_event(result_json)
        elif event_type == "tweet":
            handle_tweet_event(result_json, mq_messenger)
        else:
            handle_unknown_event(event_type, result_json)
        
    except json.JSONDecodeError as e:
        logger.error("JSON parsing error", error=str(e), traceback=traceback.format_exc(), message=message)
    except Exception as e:
        logger.error("Error processing message", error=str(e), traceback=traceback.format_exc(), message=message)



# Main function
def main(x_api_key: str) -> None:
    global mq_messenger
    
    environment = os.getenv("ENVIRONMENT", "development")
    logger.info("Starting news-powered trading system", environment=environment)
    
    # Initialize and test RabbitMQ connection at startup
    try:
        logger.info("Initializing RabbitMQ connection...")
        mq_messenger = MQMessenger.from_env(connect_on_init=True)
        
        # Test the connection
        if not mq_messenger.test_connection():
            logger.error("RabbitMQ connection test failed - shutting down")
            raise Exception("RabbitMQ connection validation failed")
        
        logger.info("RabbitMQ connection validated successfully")
        
    except Exception as e:
        logger.error(
            "Failed to establish RabbitMQ connection at startup",
            error=str(e)
        )
        raise SystemExit(1)
    
    # Create WebSocket manager with callback functions
    ws_manager = WebSocketManager(on_message, on_error, on_close, on_open)
    
    # Register signal handler for graceful shutdown using the manager
    def shutdown_handler(signum, frame):
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
