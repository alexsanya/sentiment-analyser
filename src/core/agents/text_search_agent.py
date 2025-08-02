"""Text search agent for token detection in text content."""

import time
from typing import cast
from pydantic_ai import Agent

from ...models.schemas import SentimentAnalysisResult, NoTokenFound
from ...config.logging_config import get_logger
from ...config.sentiment_config import TEXT_SEARCH_PROMPT, DEFAULT_AGENT_RETRIES
from ...config.logfire_config import create_logfire_span, log_agent_metrics

logger = get_logger(__name__)


class TextSearchAgent:
    """
    A PydanticAI agent that analyzes text and searches for new token release announcements 
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
            system_prompt=TEXT_SEARCH_PROMPT
        )
    
    async def run(self, text: str) -> SentimentAnalysisResult:
        """
        Process text to detect token announcements
        Args:
            text: The given text
            
        Returns:
            The token data if found
        """
        start_time = time.time()
        text_length = len(text)
        
        # Create Logfire span for tracing
        span = create_logfire_span(
            "text_search_agent.run",
            text_length=text_length,
            agent_type="text_search"
        )
        
        try:
            if span:
                with span:
                    result = await self.agent.run(text)
            else:
                result = await self.agent.run(text)
            
            execution_time = time.time() - start_time
            result_type = type(result.output).__name__
            
            # Log metrics to Logfire
            log_agent_metrics(
                agent_type="text_search",
                execution_time=execution_time,
                input_size=text_length,
                result_type=result_type,
                success=True,
                text_preview=text[:100] + "..." if text_length > 100 else text
            )
            
            logger.info(
                "TextSearchAgent completed analysis", 
                text_length=text_length,
                execution_time=execution_time,
                result_type=result_type
            )
            return cast(SentimentAnalysisResult, result.output)
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            # Log failed metrics to Logfire
            log_agent_metrics(
                agent_type="text_search",
                execution_time=execution_time,
                input_size=text_length,
                result_type="NoTokenFound",
                success=False,
                error=str(e)
            )
            
            logger.error(
                "TextSearchAgent failed", 
                error=str(e), 
                text_length=text_length,
                execution_time=execution_time
            )
            return NoTokenFound()