"""Handler for 'ping' event type with timestamp analysis."""

import time
from typing import Dict, Any
from logging_config import get_logger

logger = get_logger(__name__)


def handle_ping_event(result_json: Dict[str, Any]) -> None:
    """Handle 'ping' event type with timestamp analysis."""
    timestamp = result_json.get("timestamp")
    current_time_ms = time.time() * 1000
    current_time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))

    # Calculate and format time difference
    diff_time_ms = current_time_ms - timestamp
    diff_time_seconds = diff_time_ms / 1000
    diff_time_formatted = f"{int(diff_time_seconds // 60)}min{int(diff_time_seconds % 60)}sec"

    # Format original timestamp
    timestamp_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp/1000))

    logger.debug(
        "Ping received",
        current_time=current_time_str,
        message_timestamp=timestamp_str,
        time_difference_formatted=diff_time_formatted,
        time_difference_ms=diff_time_ms
    )