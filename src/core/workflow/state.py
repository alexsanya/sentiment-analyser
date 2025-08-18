"""State management for Trump-Zelenskyy workflow execution."""

from dataclasses import dataclass
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ...config.sentiment_config import SentimentConfig


@dataclass
class WorkflowState:
    """State container for Trump-Zelenskyy workflow execution."""
    text: str
    images: List[str]
    links: List[str]
    config: 'SentimentConfig'
    
    @classmethod
    def initialize(cls, text: str, images: Optional[List[str]], links: Optional[List[str]]) -> 'WorkflowState':
        """Initialize workflow state with default values."""
        from ...config.sentiment_config import get_sentiment_config
        return cls(
            text=text,
            images=images or [],
            links=links or [],
            config=get_sentiment_config()
        )