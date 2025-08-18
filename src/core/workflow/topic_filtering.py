"""Topic filtering step for Trump-Zelenskyy meeting detection."""

from typing import Optional

from ...models.schemas import TopicFilter
from ..agents import TopicFilterAgent
from ...config.logging_config import get_logger
from .state import WorkflowState

logger = get_logger(__name__)


async def run_topic_filtering_step(state: WorkflowState) -> Optional[TopicFilter]:
    """Run topic filtering for Trump-Zelenskyy meeting detection."""
    try:
        topic_filter_agent = TopicFilterAgent(agent_retries=state.config.agent_retries)
        topic_result = await topic_filter_agent.run(state.text)
        
        logger.info(
            "Topic filtering completed",
            topic_match=topic_result.topic_match,
            explanation=topic_result.explanation
        )
        
        return topic_result
        
    except Exception as e:
        logger.error(
            "Topic filtering failed",
            error=str(e),
            error_type=type(e).__name__
        )
        return None