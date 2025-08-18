"""Duplicate detector agent for preventing news duplications."""

import os
import time
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openrouter import OpenRouterProvider

from ...models.schemas import DuplicateCheckResult
from ..news_database import NewsDatabase
from ...config.logging_config import get_logger
from ...config.logfire_config import create_logfire_span, log_agent_metrics

logger = get_logger(__name__)

DUPLICATE_DETECTOR_PROMPT = '''
You are a news duplicate detection expert. Your job is to determine if a new news tweet 
conveys the same information as any existing news in the database, even if worded differently. 
Focus on the core information and facts, not the exact wording. 
Return True if the news is substantially similar to existing news, False if it's unique.
'''


class DuplicateDetectorAgent:
    """
    A PydanticAI agent that detects if news content is duplicate of existing news
    """
    
    def __init__(self, agent_retries: int = 3):
        """
        Initialize the agent with Grok-4 model via OpenRouter
        
        Args:
            agent_retries: Number of retry attempts for the agent
        """
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable is required for DuplicateDetectorAgent")
        
        model = OpenAIModel(
            'x-ai/grok-4',
            provider=OpenRouterProvider(api_key=api_key),
        )
        
        self.agent = Agent[NewsDatabase, DuplicateCheckResult](
            model=model,
            deps_type=NewsDatabase,
            result_type=DuplicateCheckResult,
            retries=agent_retries,
            system_prompt=DUPLICATE_DETECTOR_PROMPT
        )
        
        # Register the tool function
        @self.agent.tool
        async def check_against_existing_news_tool(ctx: RunContext[NewsDatabase], new_news: str) -> str:
            """Compare the new news against all existing news items in the database."""
            return DuplicateDetectorAgent.check_against_existing_news(ctx, new_news)
    
    @staticmethod
    def check_against_existing_news(ctx: RunContext[NewsDatabase], new_news: str) -> str:
        """Compare the new news against all existing news items in the database."""
        existing_news = ctx.deps.get_existing_news()
        
        if not existing_news:
            return "No existing news found in database."
        
        news_list = "\n".join([f"{i+1}. {news}" for i, news in enumerate(existing_news)])
        
        return f"""
    New news to check: "{new_news}"
    
    Existing news in database:
    {news_list}
    
    Please analyze if the new news conveys substantially the same information 
    as any of the existing news items, considering:
    - Core facts and events
    - Key people involved
    - Main outcomes or decisions
    - Geographic locations
    - Time periods mentioned
    
    Ignore differences in:
    - Exact wording or phrasing
    - Writing style
    - Minor details that don't change the core message
    """
    
    async def run(self, new_news: str, news_database: NewsDatabase) -> DuplicateCheckResult:
        """
        Check if new news is duplicate of existing news.
        
        Args:
            new_news: The new news text to check
            news_database: Database containing existing news items
            
        Returns:
            DuplicateCheckResult indicating if news is duplicate
        """
        start_time = time.time()
        text_length = len(new_news)
        
        # Create Logfire span for tracing
        span = create_logfire_span(
            "duplicate_detector_agent._run_agent",
            text_length=text_length,
            agent_type="duplicate_detector",
            existing_news_count=news_database.size()
        )
        
        try:
            if span:
                with span:
                    result = await self.agent.run(
                        f"Is this news duplicate? Check: '{new_news}'",
                        deps=news_database
                    )
            else:
                result = await self.agent.run(
                    f"Is this news duplicate? Check: '{new_news}'",
                    deps=news_database
                )
            
            execution_time = time.time() - start_time
            is_duplicate = result.output.is_duplicate
            
            # Log metrics to Logfire
            log_agent_metrics(
                agent_type="duplicate_detector",
                execution_time=execution_time,
                input_size=text_length,
                result_type=f"DuplicateCheckResult(is_duplicate={is_duplicate})",
                success=True,
                text_preview=new_news[:100] + "..." if text_length > 100 else new_news
            )
            
            logger.debug(
                "DuplicateDetectorAgent completed single attempt", 
                text_length=text_length,
                execution_time=execution_time,
                is_duplicate=is_duplicate,
                existing_news_count=news_database.size()
            )
            return result.output
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            # Log failed metrics to Logfire
            log_agent_metrics(
                agent_type="duplicate_detector",
                execution_time=execution_time,
                input_size=text_length,
                result_type="DuplicateCheckResult(is_duplicate=False)",
                success=False,
                error=str(e)
            )
            
            logger.error(
                "DuplicateDetectorAgent failed - returning safe default (not duplicate)", 
                error=str(e),
                error_type=type(e).__name__,
                text_length=text_length,
                execution_time=execution_time,
                existing_news_count=news_database.size(),
                input_preview=new_news[:100] + "..." if len(new_news) > 100 else new_news,
                fallback_behavior="is_duplicate=False (safe default - processes news)"
            )
            # Return safe default "not duplicate" to ensure important news isn't missed
            return DuplicateCheckResult(is_duplicate=False)


async def is_duplicate_news(new_news: str, existing_news: list[str]) -> bool:
    """
    Async helper function for duplicate detection.
    
    Args:
        new_news: The new news tweet to check
        existing_news: List of existing news tweets
    
    Returns:
        bool: True if duplicate, False if unique
    """
    news_db = NewsDatabase(existing_news)
    agent = DuplicateDetectorAgent()
    
    result = await agent.run(new_news, news_db)
    return result.is_duplicate