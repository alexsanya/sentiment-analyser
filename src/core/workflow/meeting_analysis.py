"""Meeting analysis step for geopolitical assessment."""

from typing import List, TYPE_CHECKING

from ...models.schemas import MeetingAnalysis
from ..agents.geo_expert_agent import GeoExpertAgent
from ...config.logging_config import get_logger

if TYPE_CHECKING:
    from ...config.sentiment_config import SentimentConfig

logger = get_logger(__name__)


async def run_meeting_analysis_step(all_news: List[str], config: 'SentimentConfig') -> MeetingAnalysis:
    """Run geo expert analysis on all accumulated news."""
    geo_expert = GeoExpertAgent(agent_retries=config.agent_retries)
    meeting_analysis = await geo_expert.run(all_news)
    
    logger.info(
        "Geo expert analysis completed",
        overall_score=meeting_analysis.overall_score,
        analyzed_outcomes=len(meeting_analysis.outcomes),
        overall_explanation=meeting_analysis.overall_explanation
    )
    
    return meeting_analysis