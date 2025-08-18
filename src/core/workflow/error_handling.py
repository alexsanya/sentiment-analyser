"""Centralized error handling for workflow steps."""

from ...models.schemas import AnalysisResult
from ...config.logging_config import get_logger

logger = get_logger(__name__)


def handle_workflow_error(error: Exception, step: str, fallback_result: AnalysisResult) -> AnalysisResult:
    """
    Centralized error handling for workflow steps.
    
    Args:
        error: The exception that occurred
        step: Name of the workflow step that failed
        fallback_result: Safe fallback result to return
        
    Returns:
        AnalysisResult with appropriate fallback behavior
    """
    logger.error(
        f"Workflow step '{step}' failed - returning safe fallback",
        error=str(error),
        error_type=type(error).__name__,
        step=step,
        fallback_type=fallback_result.analysis_type
    )
    return fallback_result