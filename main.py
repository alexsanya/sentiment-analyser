import traceback
import websocket
import json
import os
import signal
from functools import partial
from dotenv import load_dotenv
from logging_config import setup_logging, get_logger
from websocket_manager import WebSocketManager
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
            handle_tweet_event(result_json)
        else:
            handle_unknown_event(event_type, result_json)
        
    except json.JSONDecodeError as e:
        logger.error("JSON parsing error", error=str(e), traceback=traceback.format_exc(), message=message)
    except Exception as e:
        logger.error("Error processing message", error=str(e), traceback=traceback.format_exc(), message=message)



# Main function
def main(x_api_key: str) -> None:
    # Create WebSocket manager with callback functions
    ws_manager = WebSocketManager(on_message, on_error, on_close, on_open)
    
    # Register signal handler for graceful shutdown using the manager
    signal.signal(signal.SIGINT, partial(ws_manager._signal_handler))
    logger.info("Signal handler registered for graceful shutdown")
    
    environment = os.getenv("ENVIRONMENT", "development")
    logger.info("Starting news-powered trading system", environment=environment)
    
    url = "wss://ws.twitterapi.io/twitter/tweet/websocket"
    headers = {"x-api-key": x_api_key}
    
    logger.info("Connecting to Twitter.io WebSocket", url=url)
    ws_manager.connect(url, headers)
    
    logger.info("Application shutting down")

if __name__ == "__main__":
    load_dotenv()
    main(os.environ["TWITTERAPI_KEY"])
