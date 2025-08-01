"""Configuration for Logfire observability and instrumentation."""

import os
import logfire
from typing import Optional
from ..config.logging_config import get_logger

logger = get_logger(__name__)


def initialize_logfire() -> None:
    """
    Initialize Logfire with configuration from environment variables.
    
    Environment variables:
        LOGFIRE_TOKEN: The Logfire API token (required)
        LOGFIRE_SERVICE_NAME: Name of the service for tracing (default: tweets-notifier)
        LOGFIRE_ENVIRONMENT: Environment name (default: development)
        LOGFIRE_ENABLED: Enable/disable Logfire (default: true)
    """
    # Check if Logfire is enabled
    if os.getenv("LOGFIRE_ENABLED", "true").lower() != "true":
        logger.info("Logfire instrumentation disabled via LOGFIRE_ENABLED")
        return
    
    # Get configuration from environment
    token = os.getenv("LOGFIRE_TOKEN")
    service_name = os.getenv("LOGFIRE_SERVICE_NAME", "sentiment-analyzer")
    environment = os.getenv("LOGFIRE_ENVIRONMENT", os.getenv("ENVIRONMENT", "development"))
    
    if not token:
        logger.warning("LOGFIRE_TOKEN not provided - Logfire instrumentation disabled")
        return
    
    try:
        # Configure Logfire
        logfire.configure(
            token=token,
            #service_name=service_name,
            #service_version=os.getenv("SERVICE_VERSION", "0.1.0"),
            #environment=environment,
        )
        
        # Enable PydanticAI instrumentation
        logfire.instrument_pydantic_ai()
        
        logger.info(
            "Logfire initialized successfully",
            service_name=service_name,
            environment=environment
        )
        
    except Exception as e:
        logger.error("Failed to initialize Logfire", error=str(e))
        # Don't raise - let the application continue without observability


def create_logfire_span(operation: str, **kwargs) -> Optional[logfire.LogfireSpan]:
    """
    Create a Logfire span for tracking operations.
    
    Args:
        operation: The operation name for the span
        **kwargs: Additional attributes to add to the span
        
    Returns:
        Logfire span context manager or None if Logfire is not configured
    """
    try:
        return logfire.span(operation, **kwargs)
    except Exception as e:
        logger.debug("Failed to create Logfire span", operation=operation, error=str(e))
        return None


def log_agent_metrics(
    agent_type: str,
    execution_time: float,
    input_size: int,
    result_type: str,
    success: bool,
    **additional_attributes
) -> None:
    """
    Log agent execution metrics to Logfire.
    
    Args:
        agent_type: Type of agent (text, image, firecrawl)
        execution_time: Time taken for execution in seconds
        input_size: Size of input data (text length, image URL length, etc.)
        result_type: Type of result returned
        success: Whether the operation was successful
        **additional_attributes: Additional attributes to log
    """
    try:
        logfire.info(
            "Agent execution completed",
            agent_type=agent_type,
            execution_time=execution_time,
            input_size=input_size,
            result_type=result_type,
            success=success,
            **additional_attributes
        )
    except Exception as e:
        logger.debug("Failed to log agent metrics", error=str(e))


def is_logfire_enabled() -> bool:
    """Check if Logfire is enabled and configured."""
    return (
        os.getenv("LOGFIRE_ENABLED", "true").lower() == "true" and
        os.getenv("LOGFIRE_TOKEN") is not None
    )