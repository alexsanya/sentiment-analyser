import time
import traceback
import types
import websocket
from typing import Dict, Any, Optional, Callable
from logging_config import get_logger


class WebSocketManager:
    """Manages WebSocket connection lifecycle and graceful shutdown."""
    
    def __init__(
        self,
        on_message: Callable[[websocket.WebSocketApp, str], None],
        on_error: Callable[[websocket.WebSocketApp, Exception], None],
        on_close: Callable[[websocket.WebSocketApp, int, str], None],
        on_open: Callable[[websocket.WebSocketApp], None]
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
        
        Example:
            manager = WebSocketManager(
                on_message=handle_message,
                on_error=handle_error, 
                on_close=handle_close,
                on_open=handle_open
            )
        """
        self.shutdown_requested = False
        self.current_ws: Optional[websocket.WebSocketApp] = None
        self.logger = get_logger(self.__class__.__name__)
        self.on_message = on_message
        self.on_error = on_error
        self.on_close = on_close
        self.on_open = on_open
    
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
                    on_message=self.on_message,
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