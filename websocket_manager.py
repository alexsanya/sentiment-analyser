import time
import traceback
import websocket
from typing import Dict, Any, Optional, Callable
from logging_config import get_logger


class WebSocketManager:
    """Manages WebSocket connection lifecycle and graceful shutdown."""
    
    def __init__(self, on_message: Callable, on_error: Callable, on_close: Callable, on_open: Callable):
        self.shutdown_requested = False
        self.current_ws: Optional[websocket.WebSocketApp] = None
        self.logger = get_logger(self.__class__.__name__)
        self.on_message = on_message
        self.on_error = on_error
        self.on_close = on_close
        self.on_open = on_open
    
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