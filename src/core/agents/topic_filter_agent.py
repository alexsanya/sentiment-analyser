"""Topic filter agent for Putin-Trump peace talks detection."""

import os
import time
from typing import cast
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openrouter import OpenRouterProvider

from ...models.schemas import TopicFilter
from ...config.logging_config import get_logger
from ...config.logfire_config import create_logfire_span, log_agent_metrics

logger = get_logger(__name__)

TOPIC_FILTER_PROMPT = '''
## Role
You are an AI classifier specialized in analyzing news tweets.
Your task is to determine if a given tweet from one of the following mass media accounts—@BBCBreaking, @Reuters, @AP, @Axios, or @FoxNews—is related to concrete, actionable outcomes of the meeting between U.S. President Donald Trump and Ukrainian President Volodymyr Zelenskyy, scheduled for August 18, 2025, at the White House in Washington, D.C., focusing on ending Russia's war in Ukraine.

## Input
You will receive the text of a single tweet as input. Assume it is from one of the listed accounts.

## Output
Respond with exactly one of the following:
    - "Yes" if the tweet describes specific, actionable outcomes of the Trump-Zelenskyy meeting, such as concrete agreements, measurable commitments, or real policy changes (e.g., signed deals, ceasefire terms, funding pledges, or troop deployments). Use semantic and contextual analysis to confirm relevance, even if the date, location, or terms like "meeting" are omitted.
- "No" if the tweet is unrelated or only mentions ceremonial aspects (e.g., photo ops, handshakes, or general statements without actionable results).

Provide a brief 1-2 sentence explanation after your Yes/No answer, justifying your decision based on key elements in the tweet. Do not output anything else.
'''


class TopicFilterAgent:
    """
    A PydanticAI agent that analyzes text to determine if it relates to actionable outcomes from Trump-Zelenskyy meetings
    """
    
    def __init__(self, agent_retries: int = 3):
        """
        Initialize the agent with Grok-4 model via OpenRouter
        
        Args:
            agent_retries: Number of retry attempts for the agent
        """
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable is required for TopicFilterAgent")
        
        model = OpenAIModel(
            'x-ai/grok-4',
            provider=OpenRouterProvider(api_key=api_key),
        )
        
        self.agent = Agent[None, TopicFilter](
            model=model,
            result_type=TopicFilter,
            retries=agent_retries,
            system_prompt=TOPIC_FILTER_PROMPT
        )
    
    async def run(self, text: str) -> TopicFilter:
        """
        Process text to detect if it relates to actionable outcomes from Trump-Zelenskyy meetings.
        
        Args:
            text: The given text
            
        Returns:
            TopicFilter result indicating if topic matches
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
            return result.output
            
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