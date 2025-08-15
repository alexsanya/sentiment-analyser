"""Retry wrapper for agents that retries on non-TokenDetails results."""

import asyncio
import time
from typing import Callable, Awaitable, cast, Any
from ...models.schemas import SentimentAnalysisResult, TokenDetails
from ...config.logging_config import get_logger
from ...config.sentiment_config import DEFAULT_AGENT_RETRIES
from ...config.logfire_config import create_logfire_span, log_agent_metrics

logger = get_logger(__name__)


class AgentRetryWrapper:
    """
    Wrapper that retries agent execution when result is not TokenDetails.
    
    This wrapper will retry the agent run method when the result is either
    NoTokenFound or RelseaseAnnouncementWithoutDetails, up to the configured
    maximum retry attempts. Only TokenDetails results are considered successful.
    """
    
    def __init__(self, max_retries: int = DEFAULT_AGENT_RETRIES, initial_delay: float = 1.0):
        """
        Initialize the retry wrapper with exponential backoff.
        
        Args:
            max_retries: Maximum number of retry attempts
            initial_delay: Initial delay in seconds for first retry (doubles each attempt)
                          Delays: 1s, 2s, 4s, 8s for attempts 2, 3, 4, 5
        """
        self.max_retries = max_retries
        self.initial_delay = initial_delay
    
    async def run_with_retry(
        self,
        agent_run_func: Callable[..., Awaitable[SentimentAnalysisResult]],
        agent_type: str,
        *args: Any,
        **kwargs: Any
    ) -> SentimentAnalysisResult:
        """
        Execute agent run function with retry logic for non-TokenDetails results.
        
        Args:
            agent_run_func: The agent's run method to execute
            agent_type: Agent type name for logging
            *args: Arguments to pass to the agent run function
            **kwargs: Keyword arguments to pass to the agent run function
            
        Returns:
            SentimentAnalysisResult: Result from agent, potentially after retries
        """
        start_time = time.time()
        last_result = None
        
        # Create Logfire span for the entire retry process
        span = create_logfire_span(
            f"{agent_type}_retry_wrapper.run",
            agent_type=agent_type,
            max_retries=self.max_retries
        )
        
        try:
            for attempt in range(self.max_retries + 1):  # +1 for initial attempt
                attempt_start = time.time()
                
                logger.debug(
                    "Agent retry attempt",
                    agent_type=agent_type,
                    attempt=attempt + 1,
                    max_attempts=self.max_retries + 1
                )
                
                try:
                    if span:
                        with span:
                            result = await agent_run_func(*args, **kwargs)
                    else:
                        result = await agent_run_func(*args, **kwargs)
                    
                    attempt_time = time.time() - attempt_start
                    result_type = type(result).__name__
                    
                    # Check if we got TokenDetails (success condition)
                    if isinstance(result, TokenDetails):
                        total_time = time.time() - start_time
                        
                        # Log successful completion
                        log_agent_metrics(
                            agent_type=f"{agent_type}_retry",
                            execution_time=total_time,
                            input_size=len(str(args)) if args else 0,
                            result_type=result_type,
                            success=True,
                            retry_attempts=attempt + 1
                        )
                        
                        logger.info(
                            "Agent retry succeeded with TokenDetails",
                            agent_type=agent_type,
                            attempt=attempt + 1,
                            total_attempts=attempt + 1,
                            attempt_time=attempt_time,
                            total_time=total_time,
                            result_type=result_type
                        )
                        
                        return result
                    
                    # Not TokenDetails - log and potentially retry
                    last_result = result
                    
                    logger.debug(
                        "Agent retry attempt did not return TokenDetails",
                        agent_type=agent_type,
                        attempt=attempt + 1,
                        attempt_time=attempt_time,
                        result_type=result_type
                    )
                    
                    # If this was the last attempt, break without delay
                    if attempt == self.max_retries:
                        break
                    
                    # Calculate exponential backoff delay: initial_delay * (2 ** attempt)
                    delay = self.initial_delay * (2 ** attempt)
                    
                    logger.debug(
                        "Agent retry waiting before next attempt",
                        agent_type=agent_type,
                        attempt=attempt + 1,
                        next_attempt=attempt + 2,
                        delay_seconds=delay
                    )
                    
                    # Wait before next retry
                    if delay > 0:
                        await asyncio.sleep(delay)
                        
                except Exception as e:
                    # Exception occurred - let the original agent handle it
                    # This should not happen often since PydanticAI has its own retry logic
                    attempt_time = time.time() - attempt_start
                    
                    logger.error(
                        "Agent retry attempt failed with exception",
                        agent_type=agent_type,
                        attempt=attempt + 1,
                        attempt_time=attempt_time,
                        error=str(e)
                    )
                    
                    # Re-raise the exception to let normal error handling take over
                    raise
            
            # All retries exhausted without TokenDetails
            total_time = time.time() - start_time
            result_type = type(last_result).__name__ if last_result else "Unknown"
            
            # Log final failure
            log_agent_metrics(
                agent_type=f"{agent_type}_retry",
                execution_time=total_time,
                input_size=len(str(args)) if args else 0,
                result_type=result_type,
                success=False,
                retry_attempts=self.max_retries + 1,
                error="Max retries exhausted without TokenDetails"
            )
            
            logger.warning(
                "Agent retry exhausted all attempts without TokenDetails",
                agent_type=agent_type,
                total_attempts=self.max_retries + 1,
                total_time=total_time,
                final_result_type=result_type
            )
            
            # Return the last result we got
            return last_result if last_result is not None else cast(SentimentAnalysisResult, None)
            
        except Exception as e:
            total_time = time.time() - start_time
            
            # Log final exception
            log_agent_metrics(
                agent_type=f"{agent_type}_retry",
                execution_time=total_time,
                input_size=len(str(args)) if args else 0,
                result_type="Exception",
                success=False,
                error=str(e)
            )
            
            logger.error(
                "Agent retry wrapper failed with exception",
                agent_type=agent_type,
                total_time=total_time,
                error=str(e)
            )
            
            # Re-raise to let normal error handling take over
            raise