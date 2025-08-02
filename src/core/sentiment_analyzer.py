"""Sentiment analysis module for tweet token detection.

This module provides AI-powered agents for analyzing tweets to detect 
cryptocurrency token announcements in text, images, and linked URLs.
"""

from enum import Enum
from typing import List, Tuple

from ..models.schemas import SentimentAnalysisResult, NoTokenFound
from .agents import TextSearchAgent, ImageSearchAgent, FirecrawlAgent
from .utils import is_valid_solana_address, is_valid_evm_address
from ..config.sentiment_config import get_sentiment_config

class AgentType(Enum):
    """Types of sentiment analysis agents."""
    TEXT = "text"
    IMAGE = "image"
    FIRECRAWL = "firecrawl"


# Re-export for backward compatibility
__all__ = [
    'TextSearchAgent',
    'ImageSearchAgent', 
    'FirecrawlAgent',
    'AgentType',
    'merge_agent_results',
    'is_valid_solana_address',
    'is_valid_evm_address',
    'get_sentiment_config'
]


def merge_agent_results(results: List[Tuple[AgentType, SentimentAnalysisResult]]) -> SentimentAnalysisResult:
    """
    Merge multiple agent analysis results into a single result.
    
    Args:
        results: List of tuples containing (agent_type, analysis_result)
        
    Returns:
        Single merged result based on priority:
        TokenDetails > RelseaseAnnouncementWithoutDetails > NoTokenFound
        
    Note:
        Agent types are used for logging and debugging purposes.
        The actual merging logic prioritizes result types.
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
    if token_details:
        # Return the first TokenDetails found (could be enhanced to merge multiple)
        agent_type, result = token_details[0]
        return result
    elif release_announcements:
        # Return the first release announcement
        agent_type, result = release_announcements[0]
        return result
    else:
        # All were NoTokenFound
        return NoTokenFound()