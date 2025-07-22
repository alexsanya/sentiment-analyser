import json
import time
import traceback
import types
import websocket
from typing import Dict, Any, Optional, Callable
from logging_config import get_logger

# Conditional import to avoid circular dependency
try:
    from mq_messenger import MQMessenger
except ImportError:
    MQMessenger = None

# Import message handlers
from handlers import (
    handle_connected_event,
    handle_ping_event,
    handle_tweet_event,
    handle_unknown_event
)


class WebSocketManager:
    """Manages WebSocket connection lifecycle and graceful shutdown."""
    
    def __init__(
        self,
        on_message: Callable[[websocket.WebSocketApp, str], None],
        on_error: Callable[[websocket.WebSocketApp, Exception], None],
        on_close: Callable[[websocket.WebSocketApp, int, str], None],
        on_open: Callable[[websocket.WebSocketApp], None],
        mq_messenger: Optional['MQMessenger'] = None
    ):
        """Initialize WebSocketManager with callback functions.
        
        Uses dependency injection pattern to decouple WebSocket management from 
        specific message handling logic. Callbacks are invoked during WebSocket lifecycle events.
        
        Args:
            on_message: Callback for incoming WebSocket messages. 
                       Signature: (ws: WebSocketApp, message: str) -> None
            on_error: Callback for WebSocket errors and exceptions.
                     Signature: (ws: WebSocketApp, error: Exception) -> None  
            on_close: Callback for WebSocket connection closure.
                     Signature: (ws: WebSocketApp, close_code: int, close_msg: str) -> None
            on_open: Callback for successful WebSocket connection establishment.
                    Signature: (ws: WebSocketApp) -> None
            mq_messenger: Optional MQMessenger instance for message publishing.
                         If provided, enables automatic message publishing for tweet events.
        
        Example:
            manager = WebSocketManager(
                on_message=handle_message,
                on_error=handle_error, 
                on_close=handle_close,
                on_open=handle_open,
                mq_messenger=messenger
            )
        """
        self.shutdown_requested = False
        self.current_ws: Optional[websocket.WebSocketApp] = None
        self.logger = get_logger(self.__class__.__name__)
        self.on_message = on_message
        self.on_error = on_error
        self.on_close = on_close
        self.on_open = on_open
        self.mq_messenger = mq_messenger
    
    def _on_message(self, ws: websocket.WebSocketApp, message: str) -> None:
        """Main message dispatcher that routes to appropriate handlers based on event type."""
        try:
            self.logger.info("Message received", message_preview=message[:100] + "..." if len(message) > 100 else message)
            # Convert to JSON
            result_json = json.loads(message)
            event_type = result_json.get("event_type")
            
            # Route to appropriate handler based on event type
            if event_type == "connected":
                handle_connected_event(result_json)
            elif event_type == "ping":
                handle_ping_event(result_json)
            elif event_type == "tweet":
                if self.mq_messenger is not None:
                    handle_tweet_event(result_json, self.mq_messenger)
                else:
                    self.logger.error("Cannot handle tweet event: MQ messenger not initialized")
            else:
                handle_unknown_event(event_type, result_json)
            
        except json.JSONDecodeError as e:
            self.logger.error("JSON parsing error", error=str(e), traceback=traceback.format_exc(), message=message)
        except Exception as e:
            self.logger.error("Error processing message", error=str(e), traceback=traceback.format_exc(), message=message)
    
    def _signal_handler(self, signum: int, frame: types.FrameType) -> None:
        """Handle SIGINT (Ctrl+C) for graceful shutdown.
        
        Initiates shutdown sequence by setting shutdown flag and closing active WebSocket 
        connection. Designed to be registered with signal.signal() for graceful termination.
        
        Args:
            signum: Signal number (typically signal.SIGINT = 2 for Ctrl+C)
            frame: Current stack frame at time of signal (from signal handler)
            
        Side Effects:
            - Sets self.shutdown_requested = True to stop connection loop
            - Closes self.current_ws if active WebSocket connection exists
            - Logs shutdown events for monitoring and debugging
        """
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
        """Connect to WebSocket with automatic reconnection logic.
        
        Establishes persistent WebSocket connection with automatic retry on failures.
        Blocks until shutdown is requested via signal handler. Handles connection lifecycle,
        error recovery, and graceful shutdown coordination.
        
        Args:
            url: WebSocket URL to connect to (e.g., 'wss://example.com/websocket')  
            headers: HTTP headers for WebSocket handshake (e.g., {'x-api-key': 'key'})
            
        Behavior:
            - Loops until self.shutdown_requested is True
            - Creates new WebSocketApp instance for each connection attempt
            - Calls ws.run_forever() with 30s ping interval, 20s ping timeout
            - On connection failure: waits 5 seconds before retry
            - On KeyboardInterrupt or Exception: logs error and handles gracefully
            - Clears WebSocket reference in finally block for proper cleanup
            
        Raises:
            Does not raise exceptions - all errors are logged and handled internally.
            KeyboardInterrupt is caught and triggers graceful shutdown.
        """
        while not self.shutdown_requested:
            if self.shutdown_requested:
                self.logger.info("Shutdown requested, exiting connection loop")
                break
                
            try:
                ws = websocket.WebSocketApp(
                    url,
                    header=headers,
                    on_message=self.on_message if self.on_message is not None else self._on_message,
                    on_error=self.on_error,
                    on_close=self.on_close,
                    on_open=self.on_open
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