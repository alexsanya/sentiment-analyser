"""Shared schema definitions for message validation."""

from typing import List, Any, Optional, Union
from pydantic import BaseModel, Field, field_validator


class TokenDetails(BaseModel):
    """Details of token/coin in blockchain"""
    chain_id: Optional[int] = Field(None, description="Id of blockchain")
    chain_name: Optional[str] = Field(None, description="Name of blockchain")
    is_release: Optional[bool] = Field(None, description="Whether this is a token release announcement")
    chain_defined_explicitly: Optional[bool] = Field(None, description="Whether name of blockchain been mentioned explicitly in text")
    definition_fragment: Optional[str] = Field(None, description="A fragment of content where name of blockchain been mentioned explicitly")
    token_address: str = Field(..., description="Address of token")


class NoTokenFound(BaseModel):
    """When no token details found"""
    pass


class RelseaseAnnouncementWithoutDetails(BaseModel):
    """When no token details found but release is announced"""
    pass


class SnipeActionParams(BaseModel):
    """Parameters for snipe action"""
    chain_id: Optional[int] = Field(None, description="Blockchain chain ID")
    chain_name: Optional[str] = Field(None, description="Blockchain name")
    token_address: str = Field(..., description="Token contract address")


class SnipeAction(BaseModel):
    """Action message for sniping newly detected tokens"""
    action: str = Field("snipe", description="Action type")
    params: SnipeActionParams = Field(..., description="Snipe action parameters")


class TradeActionParams(BaseModel):
    """Parameters for trade action (empty for now)"""
    pass


class TradeAction(BaseModel):
    """Action message for trading based on topic sentiment"""
    action: str = Field("trade", description="Action type")
    params: TradeActionParams = Field(default_factory=TradeActionParams, description="Trade action parameters")


class TopicFilter(BaseModel):
    """Whether this is related to Trump/Putin meeting"""
    topic_match: bool = Field(description="Whether this news match the topic (Yes or No)")
    explanation: Optional[str] = Field(description="explanation after of Yes/No answer")


class AlignmentData(BaseModel):
    """How aligned Russian President Vladimir Putin and U.S. President Donald Trump after the meeting"""
    score: Optional[int] = Field(description="how aligned are both presidents on a scale from 1 to 10, or None if score is N/A")
    explanation: str = Field(description="explanation after your score (or N/A)")


# Type alias for sentiment analysis results
SentimentAnalysisResult = Union[TokenDetails, NoTokenFound, RelseaseAnnouncementWithoutDetails]

# Type alias for topic analysis results
TopicAnalysisResult = Union[TopicFilter, AlignmentData]


class AnalysisResult(BaseModel):
    """Container for analysis results with clear field names."""
    sentiment_result: Optional[SentimentAnalysisResult] = Field(None, description="Token detection analysis result")
    alignment_data: Optional[AlignmentData] = Field(None, description="Topic sentiment analysis result")
    
    @property
    def has_token_detection(self) -> bool:
        """Check if result contains token detection data."""
        return (self.sentiment_result is not None and 
                not isinstance(self.sentiment_result, NoTokenFound))
    
    @property
    def has_topic_sentiment(self) -> bool:
        """Check if result contains topic sentiment data."""
        return self.alignment_data is not None
    
    @property
    def analysis_type(self) -> str:
        """Get the type of analysis performed."""
        if self.has_token_detection:
            return "token_detection"
        elif self.has_topic_sentiment:
            return "topic_sentiment"
        else:
            return "no_analysis"
    
    @property
    def has_actionable_result(self) -> bool:
        """Check if result has actionable data for publishing actions."""
        return self.has_token_detection or self.has_topic_sentiment
    
    @classmethod
    def token_detection(cls, result: SentimentAnalysisResult) -> 'AnalysisResult':
        """Create result with token detection data."""
        return cls(sentiment_result=result, alignment_data=None)
    
    @classmethod
    def topic_sentiment(cls, data: AlignmentData) -> 'AnalysisResult':
        """Create result with topic sentiment data."""
        return cls(sentiment_result=None, alignment_data=data)
    
    @classmethod
    def no_analysis(cls) -> 'AnalysisResult':
        """Create result with no analysis data."""
        return cls(sentiment_result=None, alignment_data=None)


class DataSource(BaseModel):
    """Schema for data source"""
    name: str = Field("", description="Data source name")
    author_name: str = Field("", description="Data source author")
    author_id: str = Field("", description="Data source author id")

class TweetOutput(BaseModel):
    """Schema for transformed tweet data output"""
    data_source: DataSource = Field(default_factory=lambda: DataSource(name="", author_name="", author_id=""), description="Data source")
    createdAt: int = Field(0, description="Tweet creation datetime as unix timestamp")
    text: str = Field("", description="Tweet text content")
    media: List[str] = Field(default_factory=list, description="Media URLs from tweet")
    links: List[str] = Field(default_factory=list, description="External links from tweet")
    sentiment_analysis: Optional[SentimentAnalysisResult] = Field(None, description="Token sentiment analysis result")
    
    @field_validator('text', mode='before')
    @classmethod
    def validate_text(cls, v: Any) -> str:
        if not isinstance(v, str):
            return ""
        return v
    
    @field_validator('media', 'links', mode='before')
    @classmethod
    def validate_url_lists(cls, v: Any) -> List[str]:
        if not isinstance(v, list):
            return []
        return [url for url in v if isinstance(url, str) and url.strip()]


class TweetProcessingResult(BaseModel):
    """Container for complete tweet processing results."""
    tweet_output: TweetOutput = Field(..., description="Processed tweet data")
    analysis: AnalysisResult = Field(..., description="Analysis results")
    
    @property
    def has_actionable_result(self) -> bool:
        """Check if processing result has actionable data."""
        return self.analysis.has_actionable_result