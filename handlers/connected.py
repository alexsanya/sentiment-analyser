"""Handler for 'connected' event type."""

from typing import Dict, Any
from logging_config import get_logger

logger = get_logger(__name__)


def handle_connected_event(result_json: Dict[str, Any]) -> None:
    """Handle 'connected' event type."""
    logger.info("WebSocket connection established successfully")