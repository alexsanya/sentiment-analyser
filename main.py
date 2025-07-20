import time
import traceback
import websocket
import json
import os
from dotenv import load_dotenv
from logging_config import setup_logging, get_logger

# Initialize logger
logger = None

# Message handling callback
def on_message(ws, message):
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

            logger.info(
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
def on_error(ws, error):
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
def on_close(ws, close_status_code, close_msg):
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
def on_open(ws):
    logger.info("WebSocket connection opened successfully")

def connect_websocket(url, headers):
    while True:
        try:
            ws = websocket.WebSocketApp(
                url,
                header=headers,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close,
                on_open=on_open
            )
            
            # No automatic reconnect, handle manually
            ws.run_forever(ping_interval=30, ping_timeout=20)
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error("Connection error", error=str(e), traceback=traceback.format_exc())
            logger.info("Retrying connection in 5 seconds")
            time.sleep(5)  # Quick retry for network issues
            continue

# Main function
def main(x_api_key):
    global logger
    
    # Setup logging
    environment = os.getenv("ENVIRONMENT", "development")
    logger = setup_logging(environment)
    
    logger.info("Starting news-powered trading system", environment=environment)
    
    url = "wss://ws.twitterapi.io/twitter/tweet/websocket"
    headers = {"x-api-key": x_api_key}
    
    logger.info("Connecting to Twitter.io WebSocket", url=url)
    connect_websocket(url, headers)

if __name__ == "__main__":
    load_dotenv()
    main(os.environ["TWITTERAPI_KEY"])
