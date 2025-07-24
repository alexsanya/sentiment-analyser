"""Handler for WebSocket error events."""

import traceback
import websocket
from ..config.logging_config import get_logger

logger = get_logger(__name__)


def on_error(ws: websocket.WebSocketApp, error: Exception) -> None:
    """Handle WebSocket errors with specialized error type handling."""
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