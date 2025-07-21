"""Handler for unknown or unexpected event types."""

from typing import Dict, Any
from logging_config import get_logger

logger = get_logger(__name__)


def handle_unknown_event(event_type: str, result_json: Dict[str, Any]) -> None:
    """Handle unknown or unexpected event types."""
    logger.warning("Received unknown event type", event_type=event_type, data=result_json)