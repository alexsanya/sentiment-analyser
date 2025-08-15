"""Topic sentiment agent for Putin-Trump alignment scoring."""

import os
import time
from typing import cast
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openrouter import OpenRouterProvider

from ...models.schemas import AlignmentData
from ...config.logging_config import get_logger
from ...config.logfire_config import create_logfire_span, log_agent_metrics

logger = get_logger(__name__)

TOPIC_SENTIMENT_PROMPT = '''
# Role
You are an AI analyzer specialized in evaluating diplomatic outcomes from news tweets.
Your task is to assess, based on a given tweet from one of the following mass media accounts: @BBCBreaking, @Reuters, @AP, or @FoxNews
how aligned Russian President Vladimir Putin and U.S. President Donald Trump appear to be after their meeting on August 15, 2025, at Joint Base Elmendorf-Richardson in Anchorage, Alaska.
This summit focused on topics like a potential ceasefire in the Russia-Ukraine war.
Alignment refers to the degree of agreement, satisfaction, and positive progress reported or implied in the tweet.

## Input
You will receive the text of a single tweet as input.
Assume it is from one of the listed accounts and relates to the meeting's outcome.
Use semantic and contextual analysis to infer alignment, even if details like date, location,
explicit terms like "summit" or "meeting," or direct quotes are omitted.
Consider elements such as agreements reached, statements from parties, reactions, tone, and implications for Russia-US relations or the Ukraine conflict.

## Output
Respond with a single integer from 1 to 10, where:

- 1: The meeting made no difference; no agreements were reached, and parties remain unaligned or hostile.
- 5: Moderate progress; some agreements or discussions occurred, but alignment is partial with lingering disagreements.
- 10: The outcome exceeded expectations; both parties are highly aligned, happy with agreements, and show strong mutual satisfaction.
                    
Provide a brief 1-2 sentence explanation after your score (or N/A), justifying your decision based on key elements in the tweet. Do not output anything else.
'''


class TopicSentimentAgent:
    """
    A PydanticAI agent that analyzes text to score Putin-Trump alignment (1-10 scale)
    """
    
    def __init__(self, agent_retries: int = 3):
        """
        Initialize the agent with Grok-4 model via OpenRouter
        
        Args:
            agent_retries: Number of retry attempts for the agent
        """
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable is required for TopicSentimentAgent")
        
        model = OpenAIModel(
            'x-ai/grok-4',
            provider=OpenRouterProvider(api_key=api_key),
        )
        
        self.agent = Agent[None, AlignmentData](
            model=model,
            result_type=AlignmentData,
            retries=agent_retries,
            system_prompt=TOPIC_SENTIMENT_PROMPT
        )
    
    async def run(self, text: str) -> AlignmentData:
        """
        Process text to score Putin-Trump alignment.
        
        Args:
            text: The given text
            
        Returns:
            AlignmentData with score and explanation
        """
        start_time = time.time()
        text_length = len(text)
        
        # Create Logfire span for tracing
        span = create_logfire_span(
            "topic_sentiment_agent._run_agent",
            text_length=text_length,
            agent_type="topic_sentiment"
        )
        
        try:
            if span:
                with span:
                    result = await self.agent.run(text)
            else:
                result = await self.agent.run(text)
            
            execution_time = time.time() - start_time
            score = result.output.score
            
            # Log metrics to Logfire
            log_agent_metrics(
                agent_type="topic_sentiment",
                execution_time=execution_time,
                input_size=text_length,
                result_type=f"AlignmentData(score={score})",
                success=True,
                text_preview=text[:100] + "..." if text_length > 100 else text
            )
            
            logger.debug(
                "TopicSentimentAgent completed single attempt", 
                text_length=text_length,
                execution_time=execution_time,
                score=score,
                explanation=result.output.explanation
            )
            return result.output
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            # Log failed metrics to Logfire
            log_agent_metrics(
                agent_type="topic_sentiment",
                execution_time=execution_time,
                input_size=text_length,
                result_type="AlignmentData(score=None)",
                success=False,
                error=str(e)
            )
            
            logger.error(
                "TopicSentimentAgent failed", 
                error=str(e), 
                text_length=text_length,
                execution_time=execution_time
            )
            # Return default result on error
            return AlignmentData(score=None, explanation=f"Error during analysis: {str(e)}")