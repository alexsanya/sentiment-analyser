"""Sentiment analysis module for tweet token detection and topic analysis.

This module provides AI-powered agents for analyzing tweets to detect 
cryptocurrency token announcements in text, images, and linked URLs,
as well as topic filtering and sentiment analysis for Putin-Trump peace talks.
"""

from enum import Enum
from typing import List, Tuple, Optional

from ..models.schemas import (
    SentimentAnalysisResult,
    NoTokenFound,
    FEDDecision,
    TradeAction,
    TradeActionParams,
    AnalysisResult
)
from .agents import (
    TextSearchAgent,
    ImageSearchAgent,
    FirecrawlAgent,
    FEDDecisionAgent
)
from .utils import is_valid_solana_address, is_valid_evm_address
from ..config.sentiment_config import get_sentiment_config
from ..config.logging_config import get_logger

logger = get_logger(__name__)

class AgentType(Enum):
    """Types of sentiment analysis agents."""
    TEXT = "text"
    IMAGE = "image"
    FIRECRAWL = "firecrawl"
    FED_DECISION = "fed_decision"


def get_trade_action(fed_decision: Optional[FEDDecision]) -> Optional[TradeAction]:
    """
    Generate trade action based on Federal Reserve decision.

    Args:
        fed_decision: FEDDecision containing direction and basis points

    Returns:
        TradeAction with appropriate parameters based on rate cuts, or None if no cut

    Logic:
        - No trade action if rates haven't been lowered (decision != "DOWN")
        - Moderate trading for 25 basis points cut: leverage=5, margin_usd=300
        - Aggressive trading for >25 basis points cut: leverage=7, margin_usd=500
        - All trades: pair="ETHUSDT", side="long", take_profit=20%, stop_loss=12%
    """
    if not fed_decision or fed_decision.decision != "DOWN":
        logger.debug(f"No TradeAction for FED decision: {fed_decision.decision if fed_decision else 'None'} (not a rate cut)")
        return None

    # Parse basis points
    try:
        if fed_decision.points == "None" or not fed_decision.points:
            logger.debug("No TradeAction: basis points not specified")
            return None

        basis_points = int(fed_decision.points)
    except (ValueError, TypeError):
        logger.debug(f"No TradeAction: invalid basis points format: {fed_decision.points}")
        return None

    if basis_points <= 25:
        # Moderate trading for 25 basis points cut
        params = TradeActionParams(
            pair="ETHUSDT",
            side="long",
            leverage=5,
            margin_usd=300,
            take_profit_percent=20,
            stop_loss_percent=12
        )
        logger.debug(f"Creating moderate TradeAction for {basis_points}bp cut: leverage=5, margin=300")
    else:
        # Aggressive trading for >25 basis points cut
        params = TradeActionParams(
            pair="ETHUSDT",
            side="long",
            leverage=7,
            margin_usd=500,
            take_profit_percent=20,
            stop_loss_percent=12
        )
        logger.debug(f"Creating aggressive TradeAction for {basis_points}bp cut: leverage=7, margin=500")

    return TradeAction(action="trade", params=params)


def _get_agent_priority(agent_type: AgentType) -> int:
    """
    Get priority value for agent type (lower number = higher priority).
    
    Args:
        agent_type: The agent type to get priority for
        
    Returns:
        Priority value: TEXT=1, IMAGE=2, FIRECRAWL=3
    """
    priority_map = {
        AgentType.TEXT: 1,
        AgentType.IMAGE: 2,
        AgentType.FIRECRAWL: 3
    }
    return priority_map[agent_type]


# Re-export for backward compatibility
__all__ = [
    'TextSearchAgent',
    'ImageSearchAgent',
    'FirecrawlAgent',
    'FEDDecisionAgent',
    'AgentType',
    'merge_agent_results',
    'analyze_with_fed_priority',
    'get_trade_action',
    'is_valid_solana_address',
    'is_valid_evm_address',
    'get_sentiment_config'
]


def merge_agent_results(results: List[Tuple[AgentType, SentimentAnalysisResult]]) -> SentimentAnalysisResult:
    """
    Merge multiple agent analysis results into a single result using dual priority system.
    
    Args:
        results: List of tuples containing (agent_type, analysis_result)
        
    Returns:
        Single merged result based on dual priority system:
        
        Primary Priority (Result Type):
        TokenDetails > RelseaseAnnouncementWithoutDetails > NoTokenFound
        
        Secondary Priority (Agent Type, within same result type):
        TEXT > IMAGE > FIRECRAWL
        
    Note:
        The merging logic first groups results by type, then within each type 
        selects the result from the highest priority agent.
    """
    from ..models.schemas import TokenDetails, RelseaseAnnouncementWithoutDetails
    
    if not results:
        return NoTokenFound()
    
    # Separate results by type and track contributing agents
    token_details = []
    release_announcements = []
    no_token_found = []
    
    for agent_type, result in results:
        if isinstance(result, TokenDetails):
            token_details.append((agent_type, result))
        elif isinstance(result, RelseaseAnnouncementWithoutDetails):
            release_announcements.append((agent_type, result))
        else:  # NoTokenFound
            no_token_found.append((agent_type, result))
    
    # Priority-based merging: TokenDetails > RelseaseAnnouncementWithoutDetails > NoTokenFound
    # Within each result type, prioritize by agent: TEXT > IMAGE > FIRECRAWL
    if token_details:
        # Sort by agent priority and return result from highest priority agent
        token_details.sort(key=lambda x: _get_agent_priority(x[0]))
        agent_type, result = token_details[0]
        return result
    elif release_announcements:
        # Sort by agent priority and return result from highest priority agent
        release_announcements.sort(key=lambda x: _get_agent_priority(x[0]))
        agent_type, result = release_announcements[0]
        return result
    else:
        # All were NoTokenFound - could still prioritize by agent for consistency
        no_token_found.sort(key=lambda x: _get_agent_priority(x[0]))
        return NoTokenFound()


async def analyze_with_fed_priority(
    text: str,
    images: Optional[List[str]] = None,
    links: Optional[List[str]] = None
) -> AnalysisResult:
    """
    Analyze content with FED decision priority logic.

    Priority Order:
    1. Run FED decision agent to check for Federal Reserve rate decisions
    2. If FED decision found: Return FED decision data
    3. If no FED decision: Run token detection agents and return sentiment result

    Args:
        text: Tweet text content
        images: List of image URLs (optional)
        links: List of external links (optional)

    Returns:
        AnalysisResult containing either FED decision or token detection analysis
    """
    if images is None:
        images = []
    if links is None:
        links = []

    config = get_sentiment_config()

    # Check if workflows are enabled
    if not config.fed_analysis_enabled and not config.token_detection_enabled:
        logger.warning("Both FED analysis and token detection are disabled")
        return AnalysisResult.no_analysis()

    logger.info(
        "Starting analysis with FED-first priority",
        text_length=len(text),
        image_count=len(images),
        link_count=len(links),
        fed_analysis_enabled=config.fed_analysis_enabled,
        token_detection_enabled=config.token_detection_enabled
    )

    # Step 1: FED decision analysis (if enabled)
    if config.fed_analysis_enabled:
        try:
            fed_decision_agent = FEDDecisionAgent(agent_retries=config.agent_retries)
            fed_result = await fed_decision_agent.run(text)

            logger.info(
                "FED decision analysis completed",
                decision=fed_result.decision,
                points=fed_result.points
            )

            # If FED decision detected, return it
            if fed_result.decision != "None":
                logger.info("FED decision detected - returning FED analysis result")
                return AnalysisResult.fed_decision(fed_result)
            else:
                logger.debug("No FED decision detected - proceeding to token detection")

        except Exception as e:
            logger.error(
                "FED decision analysis failed",
                error=str(e),
                error_type=type(e).__name__
            )
            # Continue to token detection if FED analysis fails

    # Step 2: Token detection (if enabled and no FED decision found)
    if config.token_detection_enabled:
        logger.info("Running token detection agents")

        try:
            # Run existing token detection logic
            agent_results = []

            # Text analysis
            if text.strip():
                text_agent = TextSearchAgent(config.model_name)
                text_result = await text_agent.run(text)
                agent_results.append((AgentType.TEXT, text_result))

            # Image analysis
            for image_url in images:
                if image_url.strip():
                    image_agent = ImageSearchAgent(config.model_name)
                    image_result = await image_agent.run(image_url)
                    agent_results.append((AgentType.IMAGE, image_result))

            # Link analysis
            for link_url in links:
                if link_url.strip():
                    firecrawl_agent = FirecrawlAgent(config.model_name, config.firecrawl_mcp_server_url)
                    firecrawl_result = await firecrawl_agent.run(link_url)
                    agent_results.append((AgentType.FIRECRAWL, firecrawl_result))

            # Merge token detection results
            if agent_results:
                merged_result = merge_agent_results(agent_results)
                logger.debug(
                    "Token detection completed",
                    result_type=type(merged_result).__name__,
                    agent_count=len(agent_results)
                )
                return AnalysisResult.token_detection(merged_result)
            else:
                logger.debug("No token detection agents were run")
                return AnalysisResult.token_detection(NoTokenFound())

        except Exception as e:
            logger.error(
                "Token detection failed",
                error=str(e),
                error_type=type(e).__name__
            )
            return AnalysisResult.token_detection(NoTokenFound())

    # No analysis was performed
    logger.debug("No analysis was performed - all workflows disabled or failed")
    return AnalysisResult.no_analysis()