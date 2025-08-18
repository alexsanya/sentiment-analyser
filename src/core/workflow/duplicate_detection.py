"""Duplicate detection step for news processing."""

from typing import Tuple, TYPE_CHECKING

from ..agents.duplicate_detector_agent import DuplicateDetectorAgent
from ...config.logging_config import get_logger
from .state import WorkflowState

if TYPE_CHECKING:
    from ..news_database import NewsDatabase

logger = get_logger(__name__)


async def run_duplicate_detection_step(state: WorkflowState) -> Tuple[bool, 'NewsDatabase']:
    """Run duplicate detection against NewsDatabase."""
    from ..news_database import get_global_news_database
    
    news_db = get_global_news_database()
    
    duplicate_detector = DuplicateDetectorAgent(agent_retries=state.config.agent_retries)
    duplicate_result = await duplicate_detector.run(state.text, news_db)
    
    logger.info(
        "Duplicate check completed",
        is_duplicate=duplicate_result.is_duplicate,
        database_size=news_db.size()
    )
    
    return duplicate_result.is_duplicate, news_db