"""Handler for tweet message processing."""

from typing import Dict, Any
from ..config.logging_config import get_logger
from ..core.transformation import map_tweet_data
from ..models.schemas import TweetOutput

logger = get_logger(__name__)


def handle_tweet_event(tweet_data: Dict[str, Any]) -> TweetOutput:
    """Process tweet data and return transformed result.
    
    Args:
        tweet_data: Raw tweet data to process
        
    Returns:
        TweetOutput object with transformed tweet data
    """
    try:
        # Transform the tweet data
        transformed_data = map_tweet_data(tweet_data)
        
        logger.info(
            "Tweet processed successfully",
            tweet_id=tweet_data.get("id"),
            author=tweet_data.get("author", {}).get("username")
        )
        
        return transformed_data
        
    except Exception as e:
        logger.error(
            "Error processing tweet data",
            error=str(e),
            tweet_data=tweet_data
        )
        raise
    

