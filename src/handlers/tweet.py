"""Handler for tweet message processing."""

import asyncio
from typing import Dict, Any, List
from ..config.logging_config import get_logger
from ..core.transformation import map_tweet_data
from ..core.sentiment_analyzer import (
    TextSearchAgent, 
    ImageSearchAgent, 
    FirecrawlAgent,
    merge_agent_results,
    get_sentiment_config
)
from ..models.schemas import TweetOutput, SentimentAnalysisResult, NoTokenFound

logger = get_logger(__name__)


async def analyze_tweet_sentiment(tweet_output: TweetOutput) -> SentimentAnalysisResult:
    """
    Analyze tweet content for token announcements using AI agents.
    
    Args:
        tweet_output: Transformed tweet data
        
    Returns:
        Merged sentiment analysis result from all agents
    """
    try:
        config = get_sentiment_config()
        model_name = config.model_name
        firecrawl_url = config.firecrawl_mcp_server_url
        max_concurrent = config.max_concurrent_analysis
        
        # Create agents
        text_agent = TextSearchAgent(model_name=model_name)
        image_agent = ImageSearchAgent(model_name=model_name)
        firecrawl_agent = FirecrawlAgent(model_name=model_name, firecrawl_url=firecrawl_url)
        
        # Prepare tasks for concurrent execution
        tasks = []
        
        # Text analysis task
        if tweet_output.text.strip():
            tasks.append(text_agent.run(tweet_output.text))
            logger.debug("Added text analysis task", text_length=len(tweet_output.text))
        
        # Image analysis tasks (one per media URL)
        for media_url in tweet_output.media:
            if media_url.strip():
                tasks.append(image_agent.run(media_url))
                logger.debug("Added image analysis task", media_url=media_url)
        
        # URL analysis tasks (one per link)
        for link_url in tweet_output.links:
            if link_url.strip():
                tasks.append(firecrawl_agent.run(link_url))
                logger.debug("Added URL analysis task", link_url=link_url)
        
        if not tasks:
            logger.info("No content to analyze")
            return NoTokenFound()
        
        # Execute all tasks concurrently with semaphore for concurrency control
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def run_with_semaphore(task):
            async with semaphore:
                return await task
        
        # Run all tasks and gather results
        logger.info("Starting sentiment analysis", task_count=len(tasks))
        results = await asyncio.gather(*[run_with_semaphore(task) for task in tasks], return_exceptions=True)
        
        # Filter out exceptions and convert to analysis results
        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error("Agent task failed", task_index=i, error=str(result))
                valid_results.append(NoTokenFound())
            else:
                valid_results.append(result)
        
        # Merge results
        merged_result = merge_agent_results(valid_results)
        logger.info("Sentiment analysis completed", 
                   total_tasks=len(tasks), 
                   valid_results=len(valid_results),
                   result_type=type(merged_result).__name__)
        
        return merged_result
        
    except Exception as e:
        logger.error("Sentiment analysis failed", error=str(e))
        return NoTokenFound()


async def handle_tweet_event_async(tweet_data: Dict[str, Any]) -> TweetOutput:
    """Process tweet data with sentiment analysis and return transformed result.
    
    Args:
        tweet_data: Raw tweet data to process
        
    Returns:
        TweetOutput object with transformed tweet data and sentiment analysis
    """
    try:
        # Transform the tweet data
        transformed_data = map_tweet_data(tweet_data)
        
        # Perform sentiment analysis
        sentiment_result = await analyze_tweet_sentiment(transformed_data)
        
        # Add sentiment analysis to the output
        transformed_data.sentiment_analysis = sentiment_result
        
        logger.info(
            "Tweet processed successfully with sentiment analysis",
            tweet_id=tweet_data.get("id"),
            author=tweet_data.get("author_name"),
            sentiment_result_type=type(sentiment_result).__name__
        )
        
        return transformed_data
        
    except Exception as e:
        logger.error(
            "Error processing tweet data with sentiment analysis",
            error=str(e),
            tweet_data=tweet_data
        )
        raise


def handle_tweet_event(tweet_data: Dict[str, Any]) -> TweetOutput:
    """Process tweet data and return transformed result (synchronous wrapper).
    
    Args:
        tweet_data: Raw tweet data to process
        
    Returns:
        TweetOutput object with transformed tweet data and sentiment analysis
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
        # Fallback: return basic transformation without sentiment analysis
        try:
            transformed_data = map_tweet_data(tweet_data)
            transformed_data.sentiment_analysis = NoTokenFound()
            return transformed_data
        except Exception as fallback_error:
            logger.error(
                "Fallback transformation also failed",
                error=str(fallback_error),
                tweet_data=tweet_data
            )
            raise
    

