import time
import traceback
import websocket
import json
import os
from dotenv import load_dotenv

# Message handling callback
def on_message(ws, message):
    try:
        print(f"\nReceived message: {message}")
        # Convert to JSON
        result_json = json.loads(message)
        event_type = result_json.get("event_type")
        
        if event_type == "connected":
            print("Connection successful!")
            return
        if event_type == "ping":
            print("ping!")
            timestamp = result_json.get("timestamp")
            current_time_ms = time.time() * 1000
            current_time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))

            # Calculate and format time difference
            diff_time_ms = current_time_ms - timestamp
            diff_time_seconds = diff_time_ms / 1000
            diff_time_formatted = f"{int(diff_time_seconds // 60)}min{int(diff_time_seconds % 60)}sec"

            # Format original timestamp
            timestamp_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp/1000))

            # Print information
            print(f"Current time: {current_time_str}")
            print(f"Message timestamp: {timestamp_str}")
            print(f"Time difference: {diff_time_formatted} ({diff_time_ms:.0f} milliseconds)")
            return
        
        if event_type == "tweet":
            print("tweet!")
            # Extract fields
            rule_id = result_json.get("rule_id")
            rule_tag = result_json.get("rule_tag")
            event_type = result_json.get("event_type")
            tweets = result_json.get("tweets", [])
            timestamp = result_json.get("timestamp")
            
            # Print key information
            print(f"rule_id: {rule_id}")
            print(f"rule_tag: {rule_tag}")
            print(f"event_type: {event_type}")
            print(f"Number of tweets: {len(tweets)}")
            print(f"timestamp: {timestamp}")
            
            # Calculate time difference
            current_time_ms = time.time() * 1000
            current_time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
            diff_time_ms = current_time_ms - timestamp
            diff_time_seconds = diff_time_ms / 1000
            diff_time_formatted = f"{int(diff_time_seconds // 60)}min{int(diff_time_seconds % 60)}sec"
            timestamp_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp/1000))

            print(f"Current time: {current_time_str}")
            print(f"Message timestamp: {timestamp_str}")
            print(f"Time difference: {diff_time_formatted} ({diff_time_ms:.0f} milliseconds)")
        
    except json.JSONDecodeError as e:
        print(f"JSON parsing error: {e}. traceback: {traceback.format_exc()}")
    except Exception as e:
        print(f"Error occurred while processing message: {e}. traceback: {traceback.format_exc()}")

# Error handling callback
def on_error(ws, error):
    print(f"\nError occurred: {error}, traceback: {traceback.format_exc()}")
    
    if isinstance(error, websocket.WebSocketTimeoutException):
        print("Connection timeout. Please check if server is running or network connection.")
    elif isinstance(error, websocket.WebSocketBadStatusException):
        print(f"Server returned error status code: {error}")
        print("Please check if API key and endpoint path are correct.")
    elif isinstance(error, ConnectionRefusedError):
        print("Connection refused. Please confirm server address and port are correct.")

# Connection close callback
def on_close(ws, close_status_code, close_msg):
    print(f"\nConnection closed: status_code={close_status_code}, message={close_msg}")
    
    if close_status_code == 1000:
        print("Normal connection closure")
    elif close_status_code == 1001:
        print("Server is shutting down or client navigating away")
    elif close_status_code == 1002:
        print("Protocol error")
    elif close_status_code == 1003:
        print("Received unacceptable data type")
    elif close_status_code == 1006:
        print("Abnormal connection closure, possibly network issues")
    elif close_status_code == 1008:
        print("Policy violation")
    elif close_status_code == 1011:
        print("Server internal error")
    elif close_status_code == 1013:
        print("Server overloaded")

# Connection established callback
def on_open(ws):
    print("\nConnection established!")

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
            logging.error(f"Connection error: {e}")
            time.sleep(5)  # Quick retry for network issues
            continue

# Main function
def main(x_api_key):
    url = "wss://ws.twitterapi.io/twitter/tweet/websocket"
    headers = {"x-api-key": x_api_key}
    
    connect_websocket(url, headers)

if __name__ == "__main__":
    load_dotenv()
    main(os.environ["TWITTERAPI_KEY"])
