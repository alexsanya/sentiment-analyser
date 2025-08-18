"""Main workflow orchestration for Trump-Zelenskyy meeting analysis."""

from typing import Optional, List

from ...models.schemas import AnalysisResult
from ...config.logging_config import get_logger
from .state import WorkflowState
from .topic_filtering import run_topic_filtering_step
from .branches import run_meeting_analysis_branch, run_token_detection_branch

logger = get_logger(__name__)


async def analyze_with_trump_zelenskyy_workflow(
    text: str, 
    images: Optional[List[str]] = None, 
    links: Optional[List[str]] = None
) -> AnalysisResult:
    """
    Analyze content with new Trump-Zelenskyy meeting workflow.
    
    Clean orchestration of workflow steps:
    1. Initialize workflow state
    2. Topic filtering branch (if enabled)
    3. Token detection branch (if enabled and topic doesn't match)
    4. No analysis fallback
    
    Args:
        text: Tweet text content
        images: List of image URLs (optional)
        links: List of external links (optional)
        
    Returns:
        AnalysisResult containing either sentiment analysis or meeting analysis data
    """
    # Initialize workflow state
    state = WorkflowState.initialize(text, images, links)
    
    # Check if workflows are enabled
    if not state.config.topic_analysis_enabled and not state.config.token_detection_enabled:
        logger.warning("Both topic analysis and token detection are disabled")
        return AnalysisResult.no_analysis()
    
    logger.info(
        "Starting analysis with Trump-Zelenskyy workflow",
        text_length=len(state.text),
        image_count=len(state.images),
        link_count=len(state.links),
        topic_analysis_enabled=state.config.topic_analysis_enabled,
        token_detection_enabled=state.config.token_detection_enabled,
        peace_talks_enabled=state.config.peace_talks_topic_enabled
    )
    
    # Topic filtering branch (if enabled)
    if state.config.topic_analysis_enabled and state.config.peace_talks_topic_enabled:
        topic_result = await run_topic_filtering_step(state)
        
        if topic_result and topic_result.topic_match:
            return await run_meeting_analysis_branch(state)
        else:
            logger.debug("Topic does not match - proceeding to token detection")
    
    # Token detection branch (if enabled and topic didn't match)
    if state.config.token_detection_enabled:
        return await run_token_detection_branch(state)
    
    # No analysis was performed
    logger.debug("No analysis was performed - all workflows disabled or failed")
    return AnalysisResult.no_analysis()