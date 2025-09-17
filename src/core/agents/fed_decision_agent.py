"""Federal Reserve decision agent for FOMC interest rate analysis."""

import os
import time
from typing import Literal
import dspy

from ...models.schemas import FEDDecision
from ...config.logging_config import get_logger
from ...config.logfire_config import create_logfire_span, log_agent_metrics

logger = get_logger(__name__)


class FOMCNewsClassifierSimple(dspy.Signature):
    """
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
    """

    tweet_text: str = dspy.InputField(desc="Tweet content from major news sources")
    decision: Literal["UP", "DOWN", "None"] = dspy.OutputField(desc="Interest rate decision direction")
    points: str = dspy.OutputField(desc="Basis points change as integer, or 'None' if not applicable")


class FEDDecisionAgent:
    """
    A DSPy agent that analyzes text to detect Federal Reserve FOMC interest rate decisions.
    """

    def __init__(self, agent_retries: int = 3):
        """
        Initialize the agent with GPT-5 model via DSPy

        Args:
            agent_retries: Number of retry attempts for the agent
        """
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required for FEDDecisionAgent")

        # Configure DSPy with GPT-5 as specified in the FedDecision notebook
        lm = dspy.LM(
            "openai/gpt-5",
            api_key=api_key,
            api_base=os.environ.get("OPENAI_BASE_URL"),
            temperature=1.0,
            max_tokens=16000
        )
        dspy.configure(lm=lm)

        self.classifier = dspy.Predict(FOMCNewsClassifierSimple)
        self.agent_retries = agent_retries

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

        last_exception = None

        for attempt in range(self.agent_retries):
            try:
                if span:
                    with span:
                        result = self.classifier(tweet_text=text)
                else:
                    result = self.classifier(tweet_text=text)

                execution_time = time.time() - start_time
                decision = result.decision
                points = result.points

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
                    "FEDDecisionAgent completed successfully",
                    text_length=text_length,
                    execution_time=execution_time,
                    decision=decision,
                    points=points,
                    attempt=attempt + 1
                )
                return FEDDecision(decision=decision, points=points)

            except Exception as e:
                last_exception = e
                logger.warning(
                    "FEDDecisionAgent attempt failed",
                    attempt=attempt + 1,
                    max_attempts=self.agent_retries,
                    error=str(e),
                    text_length=text_length
                )

                if attempt == self.agent_retries - 1:
                    # Last attempt failed
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
                        "FEDDecisionAgent failed after all retries",
                        error=str(last_exception),
                        text_length=text_length,
                        execution_time=execution_time,
                        max_attempts=self.agent_retries
                    )
                    break

        # Return default "no decision" result on error
        return FEDDecision(decision="None", points="None")