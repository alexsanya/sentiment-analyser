import json
import re
from typing import List, Optional
from pydantic import BaseModel, Field, validator

class TweetOutput(BaseModel):
    """Schema for transformed tweet data output"""
    timestamp: Optional[str] = Field(None, description="Tweet timestamp")
    text: str = Field("", description="Tweet text content")
    media: List[str] = Field(default_factory=list, description="Media URLs from tweet")
    links: List[str] = Field(default_factory=list, description="External links from tweet")
    
    @validator('text')
    def validate_text(cls, v):
        if not isinstance(v, str):
            return ""
        return v
    
    @validator('media', 'links')
    def validate_url_lists(cls, v):
        if not isinstance(v, list):
            return []
        return [url for url in v if isinstance(url, str) and url.strip()]

def extract_url(text) -> str:
    match = re.search(r'\[.*?\]\((.*?)\)', text)
    if match:
        url = match.group(1)
        return url
    else:
        return ""

def map_tweet_data(data) -> TweetOutput:
    tweet = data["tweets"][0]

    # Extract timestamp
    timestamp = data.get("timestamp")

    # Extract text
    text = tweet.get("text", "")

    # Extract media URLs from extendedEntities
    media_entities = tweet.get("extendedEntities", {}).get("media", [])
    media = [item["expanded_url"] for item in media_entities]

    # Extract display names from entities.urls
    url_entities = tweet.get("entities", {}).get("urls", [])
    links = [extract_url(item["display_url"]) for item in url_entities if "display_url" in item]

    return TweetOutput(
        timestamp=timestamp,
        text=text,
        media=media,
        links=links
    )
