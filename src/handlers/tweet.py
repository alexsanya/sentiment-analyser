"""Handler for tweet message processing."""

import asyncio
from typing import Dict, Any, List, Awaitable, Union, Tuple, Optional
from ..config.logging_config import get_logger
from ..core.transformation import map_tweet_data
from ..core.sentiment_analyzer import (
    analyze_with_topic_priority,
    get_sentiment_config
)
from ..models.schemas import (
    TweetOutput, 
    SentimentAnalysisResult, 
    AlignmentData,
    NoTokenFound
)

logger = get_logger(__name__)


async def analyze_tweet_with_priority(tweet_output: TweetOutput) -> Tuple[Optional[SentimentAnalysisResult], Optional[AlignmentData]]:
    """
    Analyze tweet content using topic-first priority logic.
    
    Args:
        tweet_output: Transformed tweet data
        
    Returns:
        Tuple of (sentiment_result, alignment_data) where only one will be non-None
    """
    try:
        logger.info("Starting analysis with topic-first priority")
        
        # Use the new topic priority logic
        sentiment_result, alignment_data = await analyze_with_topic_priority(
            text=tweet_output.text,
            images=tweet_output.media,
            links=tweet_output.links
        )
        
        logger.info(
            "Topic-priority analysis completed",
            has_sentiment_result=sentiment_result is not None,
            has_alignment_data=alignment_data is not None,
            sentiment_type=type(sentiment_result).__name__ if sentiment_result else None,
            alignment_score=alignment_data.score if alignment_data else None
        )
        
        return sentiment_result, alignment_data
        
    except Exception as e:
        logger.error("Topic-priority analysis failed", error=str(e))
        return NoTokenFound(), None


async def handle_tweet_event_async(tweet_data: Dict[str, Any]) -> Tuple[TweetOutput, Optional[AlignmentData]]:
    """Process tweet data with topic-priority analysis and return transformed result.
    
    Args:
        tweet_data: Raw tweet data to process
        
    Returns:
        Tuple of (TweetOutput with sentiment analysis, alignment_data for trade actions)
    """
    try:
        # Transform the tweet data
        transformed_data = map_tweet_data(tweet_data)
        
        # Perform topic-priority analysis
        sentiment_result, alignment_data = await analyze_tweet_with_priority(transformed_data)
        
        # Add sentiment analysis to the output (only if we got a sentiment result)
        if sentiment_result is not None:
            transformed_data.sentiment_analysis = sentiment_result
        
        logger.info(
            "Tweet processed successfully with topic-priority analysis",
            tweet_id=tweet_data.get("id"),
            author=tweet_data.get("author_name"),
            sentiment_result_type=type(sentiment_result).__name__ if sentiment_result else None,
            has_alignment_data=alignment_data is not None,
            alignment_score=alignment_data.score if alignment_data else None
        )
        
        return transformed_data, alignment_data
        
    except Exception as e:
        logger.error(
            "Error processing tweet data with topic-priority analysis",
            error=str(e),
            tweet_data=tweet_data
        )
        raise


def handle_tweet_event(tweet_data: Dict[str, Any]) -> Tuple[TweetOutput, Optional[AlignmentData]]:
    """Process tweet data and return transformed result (synchronous wrapper).
    
    Args:
        tweet_data: Raw tweet data to process
        
    Returns:
        Tuple of (TweetOutput with sentiment analysis, alignment_data for trade actions)
    """
    try:
        # Run the async version in a new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(handle_tweet_event_async(tweet_data))
            return result
        finally:
            loop.close()
        
    except Exception as e:
        logger.error(
            "Error in synchronous tweet handler wrapper",
            error=str(e),
            tweet_data=tweet_data
        )
        # Fallback: return basic transformation without analysis
        try:
            transformed_data = map_tweet_data(tweet_data)
            transformed_data.sentiment_analysis = NoTokenFound()
            return transformed_data, None
        except Exception as fallback_error:
            logger.error(
                "Fallback transformation also failed",
                error=str(fallback_error),
                tweet_data=tweet_data
            )
            raise
    

