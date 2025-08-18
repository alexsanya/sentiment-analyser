"""Branch-specific logic for workflow execution."""

from ...models.schemas import AnalysisResult, AlignmentData, NoTokenFound
from ...config.logging_config import get_logger
from .state import WorkflowState
from .duplicate_detection import run_duplicate_detection_step
from .meeting_analysis import run_meeting_analysis_step
from .token_detection import run_token_detection_step
from .error_handling import handle_workflow_error

logger = get_logger(__name__)


async def run_meeting_analysis_branch(state: WorkflowState) -> AnalysisResult:
    """Handle the meeting analysis branch: duplicate detection → news storage → geo analysis."""
    logger.info("Topic matches Trump-Zelenskyy meeting - checking for duplicates")
    
    try:
        # Check for duplicates
        is_duplicate, news_db = await run_duplicate_detection_step(state)
        
        if not is_duplicate:
            # Add to NewsDatabase and run geo expert analysis
            news_db.add_news(state.text)
            logger.info(
                "News added to database, running geo expert analysis",
                new_database_size=news_db.size()
            )
            
            # Get all news from database for analysis
            all_news = news_db.get_existing_news()
            
            # Run geo expert analysis
            meeting_analysis = await run_meeting_analysis_step(all_news, state.config)
            
            # Create AnalysisResult for meeting analysis
            alignment_data = AlignmentData(
                score=meeting_analysis.overall_score,
                explanation=meeting_analysis.overall_explanation
            )
            
            return AnalysisResult.topic_sentiment(alignment_data)
        else:
            logger.info("News is duplicate, skipping analysis")
            return AnalysisResult.no_analysis()
            
    except Exception as e:
        fallback_result = AnalysisResult.topic_sentiment(AlignmentData(score=None, explanation=f"Meeting analysis failed: {str(e)}"))
        return handle_workflow_error(e, "meeting_analysis_branch", fallback_result)


async def run_token_detection_branch(state: WorkflowState) -> AnalysisResult:
    """Handle the token detection branch."""
    logger.info("Running token detection agents")
    
    try:
        result = await run_token_detection_step(state)
        return AnalysisResult.token_detection(result)
        
    except Exception as e:
        fallback_result = AnalysisResult.token_detection(NoTokenFound())
        return handle_workflow_error(e, "token_detection_branch", fallback_result)