"""Handler for WebSocket close events."""

import websocket
from ..config.logging_config import get_logger

logger = get_logger(__name__)


def on_close(ws: websocket.WebSocketApp, close_status_code: int, close_msg: str) -> None:
    """Handle WebSocket connection closure with status code mapping."""
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