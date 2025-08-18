"""Sentiment analysis module for tweet token detection and topic analysis.

This module provides AI-powered agents for analyzing tweets to detect 
cryptocurrency token announcements in text, images, and linked URLs,
as well as topic filtering and sentiment analysis for Trump-Zelenskyy meetings.
"""

from typing import Optional, List

from ..models.schemas import (
    TradeAction,
    TradeActionParams
)
from .agents import (
    TextSearchAgent, 
    ImageSearchAgent, 
    FirecrawlAgent,
    TopicFilterAgent
)
from .agents.duplicate_detector_agent import DuplicateDetectorAgent
from .agents.geo_expert_agent import GeoExpertAgent
from .utils import is_valid_solana_address, is_valid_evm_address
from .workflow import analyze_with_trump_zelenskyy_workflow
from .workflow.utils import AgentType, merge_agent_results
from ..config.sentiment_config import get_sentiment_config
from ..config.logging_config import get_logger

logger = get_logger(__name__)


def get_trade_action(score: Optional[int]) -> Optional[TradeAction]:
    """
    Generate trade action based on overall meeting score.
    
    Args:
        score: Overall score from MeetingAnalysis (1-10), or None if score is N/A
        
    Returns:
        TradeAction with appropriate parameters based on score, or None if score < 6
        
    Logic:
        - score < 6: No TradeAction published (returns None)
        - score 6-7: leverage=5, margin_usd=300
        - score > 7: leverage=7, margin_usd=500
        - All trades: pair="ETHUSDT", side="long", take_profit=70%/120%, stop_loss=12%
    """
    if score is None or score < 6:
        logger.debug(f"No TradeAction for score: {score} (below threshold)")
        return None
    
    if score <= 7:
        # Moderate trading for scores 6-7
        params = TradeActionParams(
            pair="ETHUSDT",
            side="long",
            leverage=5,
            margin_usd=300,
            take_profit_percent=70,
            stop_loss_percent=12
        )
        logger.debug(f"Creating moderate TradeAction for score {score}: leverage=5, margin=300")
    else:
        # Aggressive trading for scores > 7
        params = TradeActionParams(
            pair="ETHUSDT",
            side="long",
            leverage=7,
            margin_usd=500,
            take_profit_percent=120,
            stop_loss_percent=12
        )
        logger.debug(f"Creating aggressive TradeAction for score {score}: leverage=7, margin=500")
    
    return TradeAction(action="trade", params=params)




# Re-export for backward compatibility
__all__ = [
    'TextSearchAgent',
    'ImageSearchAgent', 
    'FirecrawlAgent',
    'TopicFilterAgent',
    'DuplicateDetectorAgent',
    'GeoExpertAgent',
    'AgentType',
    'merge_agent_results',
    'analyze_with_trump_zelenskyy_workflow',
    'get_trade_action',
    'is_valid_solana_address',
    'is_valid_evm_address',
    'get_sentiment_config'
]




# Keep old function for backward compatibility, but mark as deprecated
async def analyze_with_topic_priority(
    text: str, 
    images: Optional[List[str]] = None, 
    links: Optional[List[str]] = None
):
    """
    DEPRECATED: Use analyze_with_trump_zelenskyy_workflow instead.
    
    This function is kept for backward compatibility and delegates to the new workflow.
    """
    logger.warning("analyze_with_topic_priority is deprecated, use analyze_with_trump_zelenskyy_workflow")
    return await analyze_with_trump_zelenskyy_workflow(text, images, links)