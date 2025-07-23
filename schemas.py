"""Shared schema definitions for message validation."""

from typing import List, Optional, Union
from pydantic import BaseModel, Field, field_validator


class TweetOutput(BaseModel):
    """Schema for transformed tweet data output"""
    timestamp: Optional[Union[str, int]] = Field(None, description="Tweet timestamp")
    text: str = Field("", description="Tweet text content")
    media: List[str] = Field(default_factory=list, description="Media URLs from tweet")
    links: List[str] = Field(default_factory=list, description="External links from tweet")
    
    @field_validator('text')
    @classmethod
    def validate_text(cls, v):
        if not isinstance(v, str):
            return ""
        return v
    
    @field_validator('media', 'links')
    @classmethod
    def validate_url_lists(cls, v):
        if not isinstance(v, list):
            return []
        return [url for url in v if isinstance(url, str) and url.strip()]