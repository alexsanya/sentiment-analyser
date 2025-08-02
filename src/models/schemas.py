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


# Type alias for sentiment analysis results
SentimentAnalysisResult = Union[TokenDetails, NoTokenFound, RelseaseAnnouncementWithoutDetails]


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