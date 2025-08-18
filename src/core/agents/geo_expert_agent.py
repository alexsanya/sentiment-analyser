"""Geopolitical expert agent for analyzing Trump-Zelenskyy meeting outcomes."""

import os
import time
from typing import List
from dataclasses import dataclass
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openrouter import OpenRouterProvider

from ...models.schemas import MeetingAnalysis
from ...config.logging_config import get_logger
from ...config.logfire_config import create_logfire_span, log_agent_metrics

logger = get_logger(__name__)

GEO_EXPERT_PROMPT = '''
## Role
You are a geopolitical expert with comprehensive knowledge of the Russia-Ukraine conflict, including historical context, key stakeholders, ongoing military dynamics, diplomatic efforts, and potential pathways to resolution.

## Input
You will be given a list of actionable outcomes from the Trump-Zelenskyy meeting (e.g., concrete agreements, commitments, or policy changes). Assume the meeting occurred on August 18, 2025, at the White House, focusing on ending Russia's war in Ukraine.

## Task
For each actionable outcome in the list:
- Analyze its significance in the context of the Russia-Ukraine conflict.
- Rate its individual impact on the likelihood of achieving a peace deal or temporary ceasefire (1-10 scale, where 1 means it has negligible or negative effect, and 10 means it directly resolves major issues).

Then, provide an overall score (1-10) assessing how likely the combined outcomes are to lead to a peace deal or at least a temporary ceasefire within a defined timeline (e.g., weeks or months). Use this scale:
- 1: The outcomes make no difference or even reduce the chances of ceasefire/peace.
- 5: Moderate progress toward dialogue, but no binding commitments or timelines.
- 10: The end of the war is effectively announced, with a set date for implementation.

## Output
Structure your response as follows:
- For each item: [Item description] - Significance: [Brief analysis, 1-2 sentences]. Impact Score: [1-10].
- Overall Score: [1-10] - Explanation: [1-2 sentences justifying the score based on the combined outcomes].
Do not output anything else.
'''


@dataclass
class Deps:
    """Dependencies for the agent"""


class GeoExpertAgent:
    """
    A PydanticAI agent that analyzes Trump-Zelenskyy meeting outcomes for geopolitical impact
    """
    
    def __init__(self, agent_retries: int = 3):
        """
        Initialize the agent with Grok-4 model via OpenRouter
        
        Args:
            agent_retries: Number of retry attempts for the agent
        """
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable is required for GeoExpertAgent")
        
        model = OpenAIModel(
            'x-ai/grok-4',
            provider=OpenRouterProvider(api_key=api_key),
        )
        
        self.agent = Agent[Deps, MeetingAnalysis](
            model=model,
            deps_type=Deps,
            result_type=MeetingAnalysis,
            retries=agent_retries,
            system_prompt=GEO_EXPERT_PROMPT
        )
    
    async def run(self, outcomes: List[str]) -> MeetingAnalysis:
        """
        Analyze meeting outcomes for geopolitical impact and peace likelihood.
        
        Args:
            outcomes: List of actionable outcomes from Trump-Zelenskyy meeting
            
        Returns:
            MeetingAnalysis with individual outcome analysis and overall score
        """
        start_time = time.time()
        outcomes_count = len(outcomes)
        outcomes_text = "\n".join(outcomes)
        input_length = len(outcomes_text)
        
        # Create Logfire span for tracing
        span = create_logfire_span(
            "geo_expert_agent._run_agent",
            input_length=input_length,
            agent_type="geo_expert",
            outcomes_count=outcomes_count
        )
        
        try:
            if span:
                with span:
                    result = await self.agent.run(outcomes, deps=Deps())
            else:
                result = await self.agent.run(outcomes, deps=Deps())
            
            execution_time = time.time() - start_time
            overall_score = result.output.overall_score
            analyzed_outcomes = len(result.output.outcomes)
            
            # Log metrics to Logfire
            log_agent_metrics(
                agent_type="geo_expert",
                execution_time=execution_time,
                input_size=input_length,
                result_type=f"MeetingAnalysis(overall_score={overall_score})",
                success=True,
                text_preview=outcomes_text[:100] + "..." if input_length > 100 else outcomes_text
            )
            
            logger.debug(
                "GeoExpertAgent completed single attempt", 
                input_length=input_length,
                execution_time=execution_time,
                overall_score=overall_score,
                analyzed_outcomes=analyzed_outcomes,
                outcomes_count=outcomes_count,
                overall_explanation=result.output.overall_explanation
            )
            return result.output
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            # Log failed metrics to Logfire
            log_agent_metrics(
                agent_type="geo_expert",
                execution_time=execution_time,
                input_size=input_length,
                result_type="MeetingAnalysis(overall_score=1)",
                success=False,
                error=str(e)
            )
            
            logger.error(
                "GeoExpertAgent failed", 
                error=str(e), 
                input_length=input_length,
                execution_time=execution_time,
                outcomes_count=outcomes_count
            )
            # Return default low-score result on error
            from ...models.schemas import OutcomeAnalysis
            return MeetingAnalysis(
                outcomes=[
                    OutcomeAnalysis(
                        description=f"Analysis failed for {outcomes_count} outcomes",
                        significance=f"Error during analysis: {str(e)}",
                        impact_score=1
                    )
                ],
                overall_score=1,
                overall_explanation=f"Analysis failed: {str(e)}"
            )