"""Utilities for workflow processing."""

from enum import Enum
from typing import List, Tuple

from ...models.schemas import SentimentAnalysisResult, NoTokenFound


class AgentType(Enum):
    """Types of sentiment analysis agents."""
    TEXT = "text"
    IMAGE = "image"
    FIRECRAWL = "firecrawl"
    TOPIC_FILTER = "topic_filter"
    TOPIC_SENTIMENT = "topic_sentiment"


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
    from ...models.schemas import TokenDetails, RelseaseAnnouncementWithoutDetails
    
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