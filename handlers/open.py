"""Handler for WebSocket open events."""

import websocket
from logging_config import get_logger

logger = get_logger(__name__)


def on_open(ws: websocket.WebSocketApp) -> None:
    """Handle WebSocket connection opened successfully."""
    logger.info("WebSocket connection opened successfully")