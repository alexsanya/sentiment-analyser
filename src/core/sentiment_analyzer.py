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
    TopicFilter,
    AlignmentData,
    MeetingAnalysis,
    DuplicateCheckResult,
    TradeAction,
    TradeActionParams,
    AnalysisResult
)
from .agents import (
    TextSearchAgent, 
    ImageSearchAgent, 
    FirecrawlAgent,
    TopicFilterAgent
)
from .agents.duplicate_detector_agent import DuplicateDetectorAgent
from .agents.geo_expert_agent import GeoExpertAgent
from .news_database import get_global_news_database
from .utils import is_valid_solana_address, is_valid_evm_address
from ..config.sentiment_config import get_sentiment_config
from ..config.logging_config import get_logger

logger = get_logger(__name__)

class AgentType(Enum):
    """Types of sentiment analysis agents."""
    TEXT = "text"
    IMAGE = "image"
    FIRECRAWL = "firecrawl"
    TOPIC_FILTER = "topic_filter"
    TOPIC_SENTIMENT = "topic_sentiment"


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


async def analyze_with_trump_zelenskyy_workflow(
    text: str, 
    images: Optional[List[str]] = None, 
    links: Optional[List[str]] = None
) -> AnalysisResult:
    """
    Analyze content with new Trump-Zelenskyy meeting workflow.
    
    Workflow:
    1. Run topic_filter_agent to check for actionable Trump-Zelenskyy meeting outcomes
    2. If topic matches: Check for duplicates against NewsDatabase
    3. If not duplicate: Add to NewsDatabase and run geo_expert_agent analysis
    4. If topic doesn't match: Run token detection agents
    
    Args:
        text: Tweet text content
        images: List of image URLs (optional)
        links: List of external links (optional)
        
    Returns:
        AnalysisResult containing either sentiment analysis or meeting analysis data
    """
    if images is None:
        images = []
    if links is None:
        links = []
        
    config = get_sentiment_config()
    
    # Check if workflows are enabled
    if not config.topic_analysis_enabled and not config.token_detection_enabled:
        logger.warning("Both topic analysis and token detection are disabled")
        return AnalysisResult.no_analysis()
    
    logger.info(
        "Starting analysis with Trump-Zelenskyy workflow",
        text_length=len(text),
        image_count=len(images),
        link_count=len(links),
        topic_analysis_enabled=config.topic_analysis_enabled,
        token_detection_enabled=config.token_detection_enabled,
        peace_talks_enabled=config.peace_talks_topic_enabled
    )
    
    # Step 1: Topic filtering (if enabled)
    if config.topic_analysis_enabled and config.peace_talks_topic_enabled:
        try:
            topic_filter_agent = TopicFilterAgent(agent_retries=config.agent_retries)
            topic_result = await topic_filter_agent.run(text)
            
            logger.info(
                "Topic filtering completed",
                topic_match=topic_result.topic_match,
                explanation=topic_result.explanation
            )
            
            # Step 2: If topic matches, check for duplicates and analyze
            if topic_result.topic_match:
                logger.info("Topic matches Trump-Zelenskyy meeting - checking for duplicates")
                
                try:
                    # Get global news database
                    news_db = get_global_news_database()
                    
                    # Step 3: Check for duplicates
                    duplicate_detector = DuplicateDetectorAgent(agent_retries=config.agent_retries)
                    duplicate_result = await duplicate_detector.run(text, news_db)
                    
                    logger.info(
                        "Duplicate check completed",
                        is_duplicate=duplicate_result.is_duplicate,
                        database_size=news_db.size()
                    )
                    
                    if not duplicate_result.is_duplicate:
                        # Step 4: Add to NewsDatabase and run geo expert analysis
                        news_db.add_news(text)
                        logger.info(
                            "News added to database, running geo expert analysis",
                            new_database_size=news_db.size()
                        )
                        
                        # Get all news from database for analysis
                        all_news = news_db.get_existing_news()
                        
                        # Step 5: Run geo expert analysis
                        geo_expert = GeoExpertAgent(agent_retries=config.agent_retries)
                        meeting_analysis = await geo_expert.run(all_news)
                        
                        logger.info(
                            "Geo expert analysis completed",
                            overall_score=meeting_analysis.overall_score,
                            analyzed_outcomes=len(meeting_analysis.outcomes),
                            overall_explanation=meeting_analysis.overall_explanation
                        )
                        
                        # Create custom AnalysisResult for meeting analysis
                        # For now, use topic_sentiment format but with meeting data
                        alignment_data = AlignmentData(
                            score=meeting_analysis.overall_score,
                            explanation=meeting_analysis.overall_explanation
                        )
                        
                        return AnalysisResult.topic_sentiment(alignment_data)
                    else:
                        logger.info("News is duplicate, skipping analysis")
                        # Return no analysis for duplicates
                        return AnalysisResult.no_analysis()
                    
                except Exception as e:
                    logger.error(
                        "Meeting analysis workflow failed",
                        error=str(e),
                        error_type=type(e).__name__
                    )
                    # Return topic match but no analysis data
                    return AnalysisResult.topic_sentiment(AlignmentData(score=None, explanation=f"Meeting analysis failed: {str(e)}"))
            
            else:
                logger.debug("Topic does not match - proceeding to token detection")
                
        except Exception as e:
            logger.error(
                "Topic filtering failed",
                error=str(e),
                error_type=type(e).__name__
            )
            # Continue to token detection if topic filtering fails
    
    # Step 6: Token detection (if enabled and topic didn't match)
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


# Keep old function for backward compatibility, but mark as deprecated
async def analyze_with_topic_priority(
    text: str, 
    images: Optional[List[str]] = None, 
    links: Optional[List[str]] = None
) -> AnalysisResult:
    """
    DEPRECATED: Use analyze_with_trump_zelenskyy_workflow instead.
    
    This function is kept for backward compatibility and delegates to the new workflow.
    """
    logger.warning("analyze_with_topic_priority is deprecated, use analyze_with_trump_zelenskyy_workflow")
    return await analyze_with_trump_zelenskyy_workflow(text, images, links)