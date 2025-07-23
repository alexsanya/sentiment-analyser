"""Handler for 'tweet' event type with metadata extraction."""

import time
from typing import Dict, Any
from logging_config import get_logger
from mq_messenger import MQMessenger
from transformation import map_tweet_data

logger = get_logger(__name__)


def publish_tweet_event(tweet_data: Dict[str, Any], mq_messenger: MQMessenger) -> None:
    """Publish tweet event to RabbitMQ.
    
    Args:
        tweet_data: Tweet data to publish
        mq_messenger: Pre-initialized MQMessenger instance
    """
    try:
        success = mq_messenger.publish(tweet_data)
        if success:
            logger.info("Tweet event published to RabbitMQ", tweet_data=tweet_data)
        else:
            logger.warning("Failed to publish tweet event to RabbitMQ", tweet_data=tweet_data)
    except Exception as e:
        logger.error(
            "Error publishing tweet event to RabbitMQ",
            error=str(e),
            tweet_data=tweet_data
        )

def handle_tweet_event(result_json: Dict[str, Any], mq_messenger: MQMessenger) -> None:
    """Handle 'tweet' event type with metadata extraction.
    
    Args:
        result_json: Tweet event data from WebSocket
        mq_messenger: Pre-initialized MQMessenger instance
    """
    # Extract fields
    tweets = result_json.get("tweets", [])

    # iterate over tweets and extract data
    for tweet in tweets:
        if tweet.get("isReply", False):
            logger.info(
                "Skipping reply tweet",
                tweet = tweet
            )
            continue
        tweet_data = map_tweet_data(tweet)
        logger.info(
            "Tweet received",
            tweet = tweet_data
        )
        # Publish tweet event to RabbitMQ
        publish_tweet_event(tweet_data, mq_messenger)
    

