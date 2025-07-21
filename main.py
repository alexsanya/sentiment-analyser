import time
import traceback
import websocket
import json
import os
import signal
from functools import partial
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from logging_config import setup_logging, get_logger

# Initialize module-level logger
setup_logging()  # Auto-detects environment
logger = get_logger(__name__)


class WebSocketManager:
    """Manages WebSocket connection lifecycle and graceful shutdown."""
    
    def __init__(self):
        self.shutdown_requested = False
        self.current_ws: Optional[websocket.WebSocketApp] = None
        self.logger = get_logger(self.__class__.__name__)
    
    def _signal_handler(self, signum: int, frame) -> None:
        """Handle SIGINT (Ctrl+C) for graceful shutdown."""
        self.logger.info("Shutdown signal received", signal=signum)
        self.shutdown_requested = True
        
        # Close current WebSocket connection if active
        if self.current_ws is not None:
            self.logger.info("Closing WebSocket connection...")
            try:
                self.current_ws.close()
            except Exception as e:
                self.logger.error("Error closing WebSocket", error=str(e))
        
        self.logger.info("Graceful shutdown initiated")
    
    def connect(self, url: str, headers: Dict[str, str]) -> None:
        """Connect to WebSocket with automatic reconnection logic."""
        while not self.shutdown_requested:
            if self.shutdown_requested:
                self.logger.info("Shutdown requested, exiting connection loop")
                break
                
            try:
                ws = websocket.WebSocketApp(
                    url,
                    header=headers,
                    on_message=on_message,
                    on_error=on_error,
                    on_close=on_close,
                    on_open=on_open
                )
                
                # Store current WebSocket for signal handler
                self.current_ws = ws
                
                # No automatic reconnect, handle manually
                ws.run_forever(ping_interval=30, ping_timeout=20)
                
            except KeyboardInterrupt:
                self.logger.info("KeyboardInterrupt received")
                break
            except Exception as e:
                self.logger.error("Connection error", error=str(e), traceback=traceback.format_exc())
                
                # Check shutdown flag before retrying
                if self.shutdown_requested:
                    self.logger.info("Shutdown requested, not retrying connection")
                    break
                    
                self.logger.info("Retrying connection in 5 seconds")
                
                # Sleep with periodic shutdown checks
                for i in range(5):
                    if self.shutdown_requested:
                        break
                    time.sleep(1)
                continue
            finally:
                # Clear current WebSocket reference
                self.current_ws = None
        
        self.logger.info("WebSocket connection loop ended")


# Message handling callback
def on_message(ws: websocket.WebSocketApp, message: str) -> None:
    try:
        logger.info("Message received", message_preview=message[:100] + "..." if len(message) > 100 else message)
        # Convert to JSON
        result_json = json.loads(message)
        event_type = result_json.get("event_type")
        
        if event_type == "connected":
            logger.info("WebSocket connection established successfully")
            return
        if event_type == "ping":
            timestamp = result_json.get("timestamp")
            current_time_ms = time.time() * 1000
            current_time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))

            # Calculate and format time difference
            diff_time_ms = current_time_ms - timestamp
            diff_time_seconds = diff_time_ms / 1000
            diff_time_formatted = f"{int(diff_time_seconds // 60)}min{int(diff_time_seconds % 60)}sec"

            # Format original timestamp
            timestamp_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp/1000))

            logger.debug(
                "Ping received",
                current_time=current_time_str,
                message_timestamp=timestamp_str,
                time_difference_formatted=diff_time_formatted,
                time_difference_ms=diff_time_ms
            )
            return
        
        if event_type == "tweet":
            # Extract fields
            rule_id = result_json.get("rule_id")
            rule_tag = result_json.get("rule_tag")
            event_type = result_json.get("event_type")
            tweets = result_json.get("tweets", [])
            timestamp = result_json.get("timestamp")
            
            # Calculate time difference
            current_time_ms = time.time() * 1000
            current_time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
            diff_time_ms = current_time_ms - timestamp
            diff_time_seconds = diff_time_ms / 1000
            diff_time_formatted = f"{int(diff_time_seconds // 60)}min{int(diff_time_seconds % 60)}sec"
            timestamp_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp/1000))

            logger.info(
                "Tweet received",
                rule_id=rule_id,
                rule_tag=rule_tag,
                event_type=event_type,
                tweet_count=len(tweets),
                timestamp=timestamp,
                current_time=current_time_str,
                message_timestamp=timestamp_str,
                time_difference_formatted=diff_time_formatted,
                time_difference_ms=diff_time_ms
            )
        
    except json.JSONDecodeError as e:
        logger.error("JSON parsing error", error=str(e), traceback=traceback.format_exc(), message=message)
    except Exception as e:
        logger.error("Error processing message", error=str(e), traceback=traceback.format_exc(), message=message)

# Error handling callback
def on_error(ws: websocket.WebSocketApp, error: Exception) -> None:
    error_context = {"error": str(error), "traceback": traceback.format_exc()}
    
    if isinstance(error, websocket.WebSocketTimeoutException):
        logger.error("WebSocket connection timeout", **error_context, 
                    suggestion="Check if server is running or network connection")
    elif isinstance(error, websocket.WebSocketBadStatusException):
        logger.error("WebSocket bad status", **error_context,
                    suggestion="Check if API key and endpoint path are correct")
    elif isinstance(error, ConnectionRefusedError):
        logger.error("Connection refused", **error_context,
                    suggestion="Confirm server address and port are correct")
    else:
        logger.error("WebSocket error occurred", **error_context)

# Connection close callback
def on_close(ws: websocket.WebSocketApp, close_status_code: int, close_msg: str) -> None:
    close_reasons = {
        1000: "Normal connection closure",
        1001: "Server is shutting down or client navigating away",
        1002: "Protocol error",
        1003: "Received unacceptable data type",
        1006: "Abnormal connection closure, possibly network issues",
        1008: "Policy violation",
        1011: "Server internal error",
        1013: "Server overloaded"
    }
    
    reason = close_reasons.get(close_status_code, "Unknown close reason")
    
    if close_status_code == 1000:
        logger.info("WebSocket connection closed normally", 
                   status_code=close_status_code, message=close_msg, reason=reason)
    else:
        logger.warning("WebSocket connection closed unexpectedly", 
                      status_code=close_status_code, message=close_msg, reason=reason)

# Connection established callback
def on_open(ws: websocket.WebSocketApp) -> None:
    logger.info("WebSocket connection opened successfully")


# Main function
def main(x_api_key: str) -> None:
    # Create WebSocket manager
    ws_manager = WebSocketManager()
    
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
