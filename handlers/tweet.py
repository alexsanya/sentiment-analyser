"""Handler for 'tweet' event type with metadata extraction."""

import time
from typing import Dict, Any
from logging_config import get_logger
from mq_messenger import MQMessenger
from transformation import map_tweet_data

logger = get_logger(__name__)


def handle_tweet_event(result_json: Dict[str, Any], mq_messenger: MQMessenger) -> None:
    """Handle 'tweet' event type with metadata extraction.
    
    Args:
        result_json: Tweet event data from WebSocket
        mq_messenger: Pre-initialized MQMessenger instance
    """
    # Extract fields
    rule_id = result_json.get("rule_id")
    rule_tag = result_json.get("rule_tag")
    event_type = result_json.get("event_type")
    tweets = result_json.get("tweets", [])
    timestamp = result_json.get("timestamp")
    
    # Calculate time difference
    current_time_ms = time.time() * 1000
    current_time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
    diff_time_ms = current_time_ms - timestamp
    diff_time_seconds = diff_time_ms / 1000
    diff_time_formatted = f"{int(diff_time_seconds // 60)}min{int(diff_time_seconds % 60)}sec"
    timestamp_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp/1000))

    logger.info(
        "Tweet received",
        rule_id=rule_id,
        rule_tag=rule_tag,
        event_type=event_type,
        tweet_count=len(tweets),
        timestamp=timestamp,
        current_time=current_time_str,
        message_timestamp=timestamp_str,
        time_difference_formatted=diff_time_formatted,
        time_difference_ms=diff_time_ms
    )

    logger.info(result_json)
    
    # Publish tweet event to RabbitMQ
    try:
        # Create message payload with all extracted data

        mq_payload = map_tweet_data(result_json)
        
        success = mq_messenger.publish(mq_payload)
        if success:
            logger.info("Tweet event published to RabbitMQ", rule_id=rule_id, tweet_count=len(tweets))
        else:
            logger.warning("Failed to publish tweet event to RabbitMQ", rule_id=rule_id)
            
    except Exception as e:
        logger.error(
            "Error publishing tweet event to RabbitMQ",
            error=str(e),
            rule_id=rule_id,
            tweet_count=len(tweets)
        )