"""Sentiment analysis module for tweet token detection.

This module provides AI-powered agents for analyzing tweets to detect 
cryptocurrency token announcements in text, images, and linked URLs.
"""

from typing import List

from ..models.schemas import SentimentAnalysisResult, NoTokenFound
from .agents import TextSearchAgent, ImageSearchAgent, FirecrawlAgent
from .utils import is_valid_solana_address, is_valid_evm_address
from ..config.sentiment_config import get_sentiment_config

# Re-export for backward compatibility
__all__ = [
    'TextSearchAgent',
    'ImageSearchAgent', 
    'FirecrawlAgent',
    'merge_agent_results',
    'is_valid_solana_address',
    'is_valid_evm_address',
    'get_sentiment_config'
]


def merge_agent_results(results: List[SentimentAnalysisResult]) -> SentimentAnalysisResult:
    """
    Merge multiple agent analysis results into a single result.
    
    Args:
        results: List of analysis results from different agents
        
    Returns:
        Single merged result
        
    Note:
        This function is currently empty as requested - implementation will be added later
    """
    # TODO: Implement result merging logic
    # Priority: TokenDetails > RelseaseAnnouncementWithoutDetails > NoTokenFound
    # Combine multiple TokenDetails if found
    # Return most confident/complete result
    
    # For now, return first non-NoTokenFound result or NoTokenFound if all are NoTokenFound
    for result in results:
        if not isinstance(result, NoTokenFound):
            return result
    
    return NoTokenFound()