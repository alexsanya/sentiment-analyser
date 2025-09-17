"""Federal Reserve decision agent for FOMC interest rate analysis."""

import os
import time
from typing import Literal
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel

from ...models.schemas import FEDDecision
from ...config.logging_config import get_logger
from ...config.logfire_config import create_logfire_span, log_agent_metrics

logger = get_logger(__name__)

FED_DECISION_PROMPT = '''
Analyze a news tweet to identify Federal Reserve FOMC interest rate decisions from September 17, 2025.

Look for:
- Federal Reserve, Fed, FOMC mentions
- Interest rate changes (cuts, hikes, increases, decreases)
- Basis points or percentage changes
- Official policy decisions (not speculation)

Decision should be:
- "UP" for rate increases/hikes
- "DOWN" for rate cuts/decreases
- "None" for unrelated content or speculation

Points should be:
- Integer basis points (25, 50, 75, etc.)
- "None" if no specific amount mentioned
'''


class FEDDecisionAgent:
    """
    A PydanticAI agent that analyzes text to detect Federal Reserve FOMC interest rate decisions.
    """

    def __init__(self, agent_retries: int = 3):
        """
        Initialize the agent with GPT-5 model via OpenAI

        Args:
            agent_retries: Number of retry attempts for the agent
        """
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required for FEDDecisionAgent")

        # Use GPT-5 as specified in the FedDecision notebook
        model = OpenAIModel(
            'gpt-4o',
            api_key=api_key,
            temperature=1.0,
            max_tokens=16000
        )

        self.agent = Agent[None, FEDDecision](
            model=model,
            result_type=FEDDecision,
            retries=agent_retries,
            system_prompt=FED_DECISION_PROMPT
        )

    async def run(self, text: str) -> FEDDecision:
        """
        Process text to detect Federal Reserve FOMC interest rate decisions.

        Args:
            text: The given text

        Returns:
            FEDDecision result indicating direction and basis points
        """
        start_time = time.time()
        text_length = len(text)

        # Create Logfire span for tracing
        span = create_logfire_span(
            "fed_decision_agent._run_agent",
            text_length=text_length,
            agent_type="fed_decision"
        )

        try:
            if span:
                with span:
                    result = await self.agent.run(text)
            else:
                result = await self.agent.run(text)

            execution_time = time.time() - start_time
            decision = result.output.decision
            points = result.output.points

            # Log metrics to Logfire
            log_agent_metrics(
                agent_type="fed_decision",
                execution_time=execution_time,
                input_size=text_length,
                result_type=f"FEDDecision(decision={decision}, points={points})",
                success=True,
                text_preview=text[:100] + "..." if text_length > 100 else text
            )

            logger.debug(
                "FEDDecisionAgent completed single attempt",
                text_length=text_length,
                execution_time=execution_time,
                decision=decision,
                points=points
            )
            return result.output

        except Exception as e:
            execution_time = time.time() - start_time

            # Log failed metrics to Logfire
            log_agent_metrics(
                agent_type="fed_decision",
                execution_time=execution_time,
                input_size=text_length,
                result_type="FEDDecision(decision=None, points=None)",
                success=False,
                error=str(e)
            )

            logger.error(
                "FEDDecisionAgent failed",
                error=str(e),
                text_length=text_length,
                execution_time=execution_time
            )
            # Return default "no decision" result on error
            return FEDDecision(decision="None", points="None")