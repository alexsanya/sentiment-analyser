"""Topic filter agent for Putin-Trump peace talks detection."""

import os
import time
from typing import cast
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openrouter import OpenRouterProvider

from ...models.schemas import TopicFilter
from ...config.logging_config import get_logger
from ...config.sentiment_config import DEFAULT_AGENT_RETRIES
from ...config.logfire_config import create_logfire_span, log_agent_metrics
from .retry_wrapper import AgentRetryWrapper

logger = get_logger(__name__)

TOPIC_FILTER_PROMPT = '''
## Role
You are an AI classifier specialized in analyzing news tweets.
Your task is to determine if a given tweet from one of the following mass media accounts @BBCBreaking, @Reuters, @AP, or @FoxNews
is related to the outcome of the meeting between Russian President Vladimir Putin and U.S. President Donald Trump,
which occurred on August 15, 2025, at Joint Base Elmendorf-Richardson in Anchorage, Alaska.
This summit focused on topics like a potential ceasefire in the Russia-Ukraine war.

## Input
You will receive the text of a single tweet as input. Assume it is from one of the listed accounts.

## Output
Respond with exactly one of the following:
    "Yes" if the tweet is related to the meeting's outcome (e.g., decisions, agreements, statements, reactions, or results from the summit). Use semantic and contextual analysis to infer relevance, even if the date, location, or explicit terms like "summit" or "meeting" are omitted. For example, references to Putin-Trump talks, Russia-US diplomacy, Ukraine ceasefire announcements, or post-meeting developments could qualify.
    "No" if the tweet is unrelated (e.g., about other events, general news, or topics not tied to this specific meeting's results).

Provide a brief 1-2 sentence explanation after your Yes/No answer, justifying your decision based on key elements in the tweet. Do not output anything else.
'''


class TopicFilterAgent:
    """
    A PydanticAI agent that analyzes text to determine if it relates to Putin-Trump peace talks
    """
    
    def __init__(self):
        """
        Initialize the agent with Grok-4 model via OpenRouter
        """
        model = OpenAIModel(
            'x-ai/grok-4',
            provider=OpenRouterProvider(api_key=os.getenv("OPENROUTER_API_KEY")),
        )
        
        self.agent = Agent[None, TopicFilter](  # type: ignore[call-overload]
            model=model,
            result_type=TopicFilter,
            retries=0,  # Disable PydanticAI retries, use our custom retry wrapper
            system_prompt=TOPIC_FILTER_PROMPT
        )
        self.retry_wrapper = AgentRetryWrapper(max_retries=DEFAULT_AGENT_RETRIES)
    
    async def run(self, text: str) -> TopicFilter:
        """
        Process text to detect if it relates to Putin-Trump peace talks.
        
        Args:
            text: The given text
            
        Returns:
            TopicFilter result indicating if topic matches
        """
        return await self.retry_wrapper.run_with_retry(
            self._run_agent,
            "topic_filter",
            text
        )
    
    async def _run_agent(self, text: str) -> TopicFilter:
        """
        Internal method to run the agent without retry logic.
        
        Args:
            text: The given text
            
        Returns:
            TopicFilter result
        """
        start_time = time.time()
        text_length = len(text)
        
        # Create Logfire span for tracing
        span = create_logfire_span(
            "topic_filter_agent._run_agent",
            text_length=text_length,
            agent_type="topic_filter"
        )
        
        try:
            if span:
                with span:
                    result = await self.agent.run(text)
            else:
                result = await self.agent.run(text)
            
            execution_time = time.time() - start_time
            topic_match = result.output.topic_match
            
            # Log metrics to Logfire
            log_agent_metrics(
                agent_type="topic_filter",
                execution_time=execution_time,
                input_size=text_length,
                result_type=f"TopicFilter(match={topic_match})",
                success=True,
                text_preview=text[:100] + "..." if text_length > 100 else text
            )
            
            logger.debug(
                "TopicFilterAgent completed single attempt", 
                text_length=text_length,
                execution_time=execution_time,
                topic_match=topic_match,
                explanation=result.output.explanation
            )
            return cast(TopicFilter, result.output)
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            # Log failed metrics to Logfire
            log_agent_metrics(
                agent_type="topic_filter",
                execution_time=execution_time,
                input_size=text_length,
                result_type="TopicFilter(match=False)",
                success=False,
                error=str(e)
            )
            
            logger.error(
                "TopicFilterAgent failed", 
                error=str(e), 
                text_length=text_length,
                execution_time=execution_time
            )
            # Return default "no match" result on error
            return TopicFilter(topic_match=False, explanation=f"Error during analysis: {str(e)}")