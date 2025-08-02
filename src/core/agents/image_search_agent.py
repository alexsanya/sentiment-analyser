"""Image search agent for token detection in image content."""

import time
from typing import cast
from pydantic_ai import Agent, ImageUrl

from ...models.schemas import SentimentAnalysisResult, NoTokenFound
from ...config.logging_config import get_logger
from ...config.sentiment_config import IMAGE_SEARCH_PROMPT, DEFAULT_AGENT_RETRIES
from ...config.logfire_config import create_logfire_span, log_agent_metrics

logger = get_logger(__name__)


class ImageSearchAgent:
    """
    A PydanticAI agent that analyzes images and searches for new token release announcements 
    """
    
    def __init__(self, model_name: str = "openai:gpt-4o"):
        """
        Initialize the agent
        
        Args:
            model_name: The LLM model to use (default: gpt-4o)
        """
        self.agent = Agent[None, SentimentAnalysisResult](  # type: ignore[call-overload]
            model=model_name,
            result_type=SentimentAnalysisResult,
            retries=DEFAULT_AGENT_RETRIES,
            system_prompt=IMAGE_SEARCH_PROMPT
        )
    
    async def run(self, image_url: str) -> SentimentAnalysisResult:
        """
        Process image to detect token announcements
        Args:
            image_url: The url of an image
            
        Returns:
            The token data if found
        """
        start_time = time.time()
        url_length = len(image_url)
        
        # Create Logfire span for tracing
        span = create_logfire_span(
            "image_search_agent.run",
            image_url=image_url,
            url_length=url_length,
            agent_type="image_search"
        )
        
        try:
            if span:
                with span:
                    result = await self.agent.run([ImageUrl(url=image_url)])
            else:
                result = await self.agent.run([ImageUrl(url=image_url)])
            
            execution_time = time.time() - start_time
            result_type = type(result.output).__name__
            
            # Log metrics to Logfire
            log_agent_metrics(
                agent_type="image_search",
                execution_time=execution_time,
                input_size=url_length,
                result_type=result_type,
                success=True,
                image_url=image_url
            )
            
            logger.info(
                "ImageSearchAgent completed analysis", 
                image_url=image_url,
                execution_time=execution_time,
                result_type=result_type
            )
            return cast(SentimentAnalysisResult, result.output)
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            # Log failed metrics to Logfire
            log_agent_metrics(
                agent_type="image_search",
                execution_time=execution_time,
                input_size=url_length,
                result_type="NoTokenFound",
                success=False,
                error=str(e),
                image_url=image_url
            )
            
            logger.error(
                "ImageSearchAgent failed", 
                error=str(e), 
                image_url=image_url,
                execution_time=execution_time
            )
            return NoTokenFound()